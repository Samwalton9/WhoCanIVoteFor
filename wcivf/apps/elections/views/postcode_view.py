from icalendar import Calendar, Event, vText
from django.utils import timezone
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import TemplateView, View

from core.helpers import clean_postcode
from elections.dummy_models import DummyPostElection
from parishes.models import ParishCouncilElection
from .mixins import (
    LogLookUpMixin,
    PostcodeToPostsMixin,
    PollingStationInfoMixin,
    PostelectionsToPeopleMixin,
    NewSlugsRedirectMixin,
)
from elections.models import InvalidPostcodeError


class PostcodeView(
    NewSlugsRedirectMixin,
    PostcodeToPostsMixin,
    PollingStationInfoMixin,
    LogLookUpMixin,
    TemplateView,
    PostelectionsToPeopleMixin,
):
    """
    This is the main view that takes a postcode and shows all elections
    for that area, with related information.

    This is really the main destination page of the whole site, so there is a
    high chance this will need to be split out in to a few mixins, and cached
    well.
    """

    template_name = "elections/postcode_view.html"
    pk_url_kwarg = "postcode"
    ballots = None
    postcode = None
    parish_council_election = None

    def get_ballots(self):
        """
        Returns a QuerySet of PostElection objects. Calls postcode_to_ballots
        and updates the self.ballots attribute the first time it is called.
        """
        if self.ballots is None:
            self.ballots = self.postcode_to_ballots(postcode=self.postcode)

        return self.ballots

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.postcode = clean_postcode(kwargs["postcode"])
        self.log_postcode(self.postcode)

        context["postcode"] = self.postcode

        try:
            context["postelections"] = self.get_ballots()
            entry = settings.POSTCODE_LOGGER.entry_class(
                postcode=self.postcode,
                dc_product=settings.POSTCODE_LOGGER.dc_product.wcivf,
                **self.request.session.get("utm_data"),
            )
            settings.POSTCODE_LOGGER.log(entry)
        except InvalidPostcodeError as exception:
            raise exception

        context["show_polling_card"] = self.show_polling_card(
            context["postelections"]
        )
        context["people_for_post"] = {}
        for postelection in context["postelections"]:
            postelection.people = self.people_for_ballot(postelection)

        context["polling_station"] = self.get_polling_station_info(
            context["postcode"]
        )

        context[
            "advance_voting_station"
        ] = self.get_advance_voting_station_info(context["polling_station"])

        context["ballots_today"] = self.get_todays_ballots()
        context[
            "multiple_city_of_london_elections_today"
        ] = self.multiple_city_of_london_elections_today()
        context["referendums"] = list(self.get_referendums())
        context["parish_council_election"] = self.get_parish_council_election()
        context["num_ballots"] = self.num_ballots()

        return context

    def get_todays_ballots(self):
        """
        Return a list of ballots filtered by whether they are today
        """
        return [
            ballot for ballot in self.ballots if ballot.election.is_election_day
        ]

    def get_referendums(self):
        """
        Yield all referendums associated with the ballots for this postcode.
        After 6th May return an empty list to avoid displaying unwanted
        information
        """
        if (
            timezone.datetime.today().date()
            > timezone.datetime(2021, 5, 6).date()
        ):
            return []

        for ballot in self.ballots:
            yield from ballot.referendums.all()

    def multiple_city_of_london_elections_today(self):
        """
        Checks if there are multiple elections taking place today in the City
        of London. This is used to determine if it is safe to display polling
        station open/close times in the template. As if there are multiple then
        it is unclear what time the polls would be open. See this issue for
        more info https://github.com/DemocracyClub/WhoCanIVoteFor/issues/441
        """
        ballots = self.get_todays_ballots()

        # if only one ballot can return early
        if len(ballots) <= 1:
            return False

        if not any(
            [ballot for ballot in ballots if ballot.election.is_city_of_london]
        ):
            return False

        # get unique elections and return whether more than 1
        return len({ballot.election.slug for ballot in ballots}) > 1

    def get_parish_council_election(self):
        """
        Check if we have any ballots with a parish council, if not return an
        empty QuerySet. If we do, return the first object we find. This may seem
        arbritary to only use the first object we find but in practice we only
        assign a single parish council for to a single english local election
        ballot. So in practice we should only ever find one object.
        """
        if self.parish_council_election is not None:
            return self.parish_council_election

        ballots_with_parishes = self.ballots.filter(num_parish_councils__gt=0)
        if not ballots_with_parishes:
            return None

        self.parish_council_election = ParishCouncilElection.objects.filter(
            ballots__in=self.ballots
        ).first()
        return self.parish_council_election

    def num_ballots(self):
        """
        Calculate the number of ballots there will be to fill in, accounting for
        the any parish council ballots if a contested parish council election is
        taking place in the future
        """
        num_ballots = len(
            [ballot for ballot in self.ballots if not ballot.past_date]
        )

        if not self.parish_council_election:
            return num_ballots

        if self.parish_council_election.in_past:
            return num_ballots

        if self.parish_council_election.is_contested:
            num_ballots += 1

        return num_ballots


class PostcodeiCalView(
    NewSlugsRedirectMixin, PostcodeToPostsMixin, View, PollingStationInfoMixin
):

    pk_url_kwarg = "postcode"

    def get(self, request, *args, **kwargs):
        postcode = kwargs["postcode"]
        try:
            ballots = self.postcode_to_ballots(postcode=postcode)
        except InvalidPostcodeError:
            return HttpResponseRedirect(
                f"/?invalid_postcode=1&postcode={postcode}"
            )

        polling_station = self.get_polling_station_info(postcode)

        cal = Calendar()
        cal["summary"] = "Elections in {}".format(postcode)
        cal["X-WR-CALNAME"] = "Elections in {}".format(postcode)
        cal["X-WR-TIMEZONE"] = "Europe/London"

        cal.add("version", "2.0")
        cal.add("prodid", "-//Elections in {}//mxm.dk//".format(postcode))

        for post_election in ballots:
            if post_election.cancelled:
                continue
            event = Event()
            event["uid"] = "{}-{}".format(
                post_election.post.ynr_id, post_election.election.slug
            )
            event["summary"] = "{} - {}".format(
                post_election.election.name, post_election.post.label
            )
            event.add("dtstamp", timezone.now())
            event.add("dtstart", post_election.election.start_time)
            event.add("dtend", post_election.election.end_time)
            event.add(
                "DESCRIPTION",
                "Find out more at {}/elections/{}/".format(
                    settings.CANONICAL_URL, postcode.replace(" ", "")
                ),
            )
            if polling_station.get("polling_station_known"):
                geometry = polling_station["polling_station"]["geometry"]
                if geometry:
                    event["geo"] = "{};{}".format(
                        geometry["coordinates"][0], geometry["coordinates"][1]
                    )
                properties = polling_station["polling_station"]["properties"]
                event["location"] = vText(
                    "{}, {}".format(
                        properties["address"].replace("\n", ", "),
                        properties["postcode"],
                    )
                )

            cal.add_component(event)

            # add hustings events if there are any in the future
            for husting in post_election.husting_set.future():
                event = Event()
                event["uid"] = husting.uuid
                event["summary"] = husting.title
                event.add("dtstamp", timezone.now())
                event.add("dtstart", husting.starts)
                if husting.ends:
                    event.add("dtend", husting.ends)
                event.add("DESCRIPTION", f"Find out more at {husting.url}")
                cal.add_component(event)

        return HttpResponse(cal.to_ical(), content_type="text/calendar")


class DummyPostcodeView(PostcodeView):
    postcode = None

    def get(self, request, *args, **kwargs):
        kwargs["postcode"] = self.postcode
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = kwargs
        self.postcode = clean_postcode(kwargs["postcode"])
        context["postcode"] = self.postcode
        context["postelections"] = self.get_ballots()
        context["show_polling_card"] = True
        context["polling_station"] = {}
        context["num_ballots"] = 1

        return context

    def get_ballots(self):
        return [DummyPostElection()]
