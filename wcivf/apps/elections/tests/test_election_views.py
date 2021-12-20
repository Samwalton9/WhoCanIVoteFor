import pytest
from django.shortcuts import reverse
from django.test import TestCase
from django.test.utils import override_settings
from elections.models import Post
from elections.tests.factories import (
    ElectionFactory,
    ElectionFactoryLazySlug,
    ElectionWithPostFactory,
    PostElectionFactory,
    PostFactory,
)
from people.tests.factories import PersonFactory, PersonPostFactory
from pytest_django.asserts import assertContains, assertNotContains
from elections.views import PostView


@override_settings(
    STATICFILES_STORAGE="pipeline.storage.NonPackagingPipelineStorage",
    PIPELINE_ENABLED=False,
)
class ElectionViewTests(TestCase):
    def setUp(self):
        self.election = ElectionWithPostFactory(
            name="City of London Corporation local election",
            election_date="2017-03-23",
            slug="local.city-of-london.2017-03-23",
        )

    def test_election_list_view(self):
        with self.assertNumQueries(2):
            url = reverse("elections_view")
            response = self.client.get(url, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "elections/elections_view.html")
            self.assertContains(response, self.election.nice_election_name)

    def test_election_detail_view(self):
        response = self.client.get(
            self.election.get_absolute_url(), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "elections/election_view.html")
        self.assertContains(response, self.election.nice_election_name)

    @pytest.mark.freeze_time("2017-03-23")
    def test_election_detail_day_of_election(self):
        """
        Test the wording of poll open/close times for both an election within
        City of London, and for another election not in City of London
        """
        not_city_of_london = ElectionFactory(
            slug="not.city-of-london",
            election_date="2017-03-23",
        )
        PostElectionFactory(election=not_city_of_london)
        for election in [
            (self.election, "Polls are open from 8a.m. till 8p.m."),
            (not_city_of_london, "Polls are open from 7a.m. till 10p.m."),
        ]:
            with self.subTest(election=election):
                response = self.client.get(
                    election[0].get_absolute_url(), follow=True
                )
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(
                    response, "elections/election_view.html"
                )
                self.assertContains(response, election[0].nice_election_name)
                self.assertContains(response, election[1])

    def test_division_name_displayed(self):
        """
        For each Post.DIVISION_TYPE, creates an elections, gets a response for
        from the ElectionDetail view, and checks that the response contains the
        correct value for division name .e.g Ward
        """
        Post.DIVISION_TYPE_CHOICES.append(("", ""))
        for division_type in Post.DIVISION_TYPE_CHOICES:
            election = ElectionWithPostFactory(
                ballot__post__division_type=division_type[0]
            )
            with self.subTest(election=election):
                response = self.client.get(
                    election.get_absolute_url(), follow=True
                )
                self.assertContains(
                    response, election.pluralized_division_name.title()
                )


class ElectionPostViewTests(TestCase):
    def setUp(self):
        self.election = ElectionFactory(
            name="Adur local election",
            election_date="2021-05-06",
            slug="local.adur.churchill.2021-05-06",
        )
        self.post = PostFactory(label="Adur local election")
        self.post_election = PostElectionFactory(
            election=self.election, post=self.post
        )

    def test_zero_candidates(self):
        response = self.client.get(
            self.post_election.get_absolute_url(), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "elections/post_view.html")
        self.assertTemplateUsed(
            response, "elections/includes/_post_meta_title.html"
        )
        self.assertTemplateUsed(
            response, "elections/includes/_post_meta_description.html"
        )
        self.assertContains(response, "No candidates known yet.")

    def test_num_candidates(self):
        people = [PersonFactory() for p in range(5)]
        for person in people:
            PersonPostFactory(
                post_election=self.post_election,
                election=self.election,
                post=self.post,
                person=person,
            )

        response = self.client.get(
            self.post_election.get_absolute_url(), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "elections/post_view.html")
        self.assertTemplateUsed(
            response, "elections/includes/_post_meta_title.html"
        )
        self.assertTemplateUsed(
            response, "elections/includes/_post_meta_description.html"
        )
        self.assertContains(response, f"The 5 candidates in {self.post.label}")
        self.assertContains(
            response, f"See all 5 candidates in the {self.post.label}"
        )

    def test_cancelled_election_with_candidates(self):
        self.post_election.winner_count = 4
        people = [PersonFactory() for p in range(4)]
        for person in people:
            PersonPostFactory(
                post_election=self.post_election,
                election=self.election,
                post=self.post,
                person=person,
            )
        self.post_election.cancelled = True
        self.post_election.save()
        response = self.client.get(
            self.post_election.get_absolute_url(), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "elections/post_view.html")
        self.assertTemplateUsed(
            response, "elections/includes/_post_meta_title.html"
        )
        self.assertTemplateUsed(
            response, "elections/includes/_post_meta_description.html"
        )
        self.assertNotContains(response, "No candidates known yet.")
        self.assertContains(
            response,
            f"{self.post_election.election.name}: This election has been cancelled",
        )

    def test_cancelled_election_without_candidates(self):
        self.post_election.winner_count = 4
        self.post_election.cancelled = True
        self.post_election.save()
        response = self.client.get(
            self.post_election.get_absolute_url(), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "elections/post_view.html")
        self.assertTemplateUsed(
            response, "elections/includes/_post_meta_title.html"
        )
        self.assertTemplateUsed(
            response, "elections/includes/_post_meta_description.html"
        )
        self.assertNotContains(response, "No candidates known yet.")
        self.assertContains(
            response,
            f"{self.post_election.election.name}: This election has been cancelled",
        )

    # In the case of fewer candidates than seats but where number of candidates is one or more
    def test_uncontested_and_rescheduled(self):
        self.post_election.winner_count = 5
        people = [PersonFactory() for p in range(4)]
        for person in people:
            PersonPostFactory(
                post_election=self.post_election,
                election=self.election,
                post=self.post,
                person=person,
            )
        self.post_election.contested = False
        self.post_election.metadata = None
        self.post_election.cancelled = True
        self.post_election.save()

        response = self.client.get(
            self.post_election.get_absolute_url(), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "elections/includes/_cancelled_election.html"
        )

        self.assertContains(
            response,
            "This election was uncontested because the number of candidates who stood was fewer than the number of available seats.",
        )
        self.assertNotContains(response, "This election was cancelled.")

    # In the case where candidates and seats are equal
    def test_uncontested_and_elected(self):
        self.post_election.winner_count = 4
        people = [PersonFactory() for p in range(4)]
        for person in people:
            PersonPostFactory(
                post_election=self.post_election,
                election=self.election,
                post=self.post,
                person=person,
            )
        self.post_election.contested = False
        self.post_election.cancelled = True
        self.post_election.metadata = None
        self.post_election.save()
        response = self.client.get(
            self.post_election.get_absolute_url(), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "elections/includes/_cancelled_election.html"
        )
        self.assertContains(response, "Uncontested Election")
        self.assertContains(
            response,
            "No votes will be cast, and the candidates below have been automatically declared",
        )
        self.assertNotContains(response, "This election was cancelled.")

    # In the case where no one turns up at all
    def test_no_candidates_turn_up(self):
        self.post_election.winner_count = 4
        self.post_election.contested = False
        self.post_election.cancelled = True
        self.post_election.metadata = None
        self.post_election.save()
        response = self.client.get(
            self.post_election.get_absolute_url(), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "elections/includes/_cancelled_election.html"
        )
        self.assertContains(
            response,
            "Rescheduled Election",
        )
        self.assertContains(response, "This election will not take place")
        self.assertContains(
            response,
            "A new election to fill the unclaimed seats will be held within 35 working days of the original election date.",
        )


@pytest.mark.django_db
class TestPostViewName:
    @pytest.fixture(params=Post.DIVISION_TYPE_CHOICES)
    def post_obj(self, request):
        """
        Fixture to create a Post object with each division choice
        """
        return PostFactory(division_type=request.param[0])

    def test_name_correct(self, post_obj, client):
        """
        Test that the correct names for the post and post election objects are
        displayed
        """
        post_election = PostElectionFactory(post=post_obj)

        response = client.get(
            post_election.get_absolute_url(),
            follow=True,
        )
        assertContains(response, post_election.friendly_name)
        assertContains(response, post_election.post.full_label)

    def test_by_election(self, client):
        """
        Test for by elections
        """
        post_election = PostElectionFactory(
            ballot_paper_id="local.by.election.2020",
            election__any_non_by_elections=False,
        )

        response = client.get(post_election.get_absolute_url(), follow=True)
        assertContains(response, "by-election")
        assertContains(response, post_election.friendly_name)
        assertContains(response, post_election.post.label)


class TestPostViewNextElection:
    @pytest.mark.django_db
    @pytest.mark.freeze_time("2021-5-1")
    def test_next_election_displayed(self, client):
        post = PostFactory()
        past = PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2019-5-2",
                current=False,
            ),
        )
        # create a future election expected to be displayed
        PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2021-5-6",
                current=True,
            ),
        )

        response = client.get(past.get_absolute_url(), follow=True)
        assertContains(response, "<h3>Next election</h3>")
        assertContains(
            response,
            "due to take place <strong>on Thursday 6 May 2021</strong>.",
        )

    @pytest.mark.django_db
    @pytest.mark.freeze_time("2021-5-1")
    def test_next_election_not_displayed(self, client):
        post = PostFactory()
        past = PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2019-5-2",
                current=False,
            ),
        )
        response = client.get(past.get_absolute_url(), follow=True)
        assertNotContains(response, "<h3>Next election</h3>")

    @pytest.mark.django_db
    @pytest.mark.freeze_time("2021-5-7")
    def test_next_election_not_displayed_in_past(self, client):
        post = PostFactory()
        past = PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2019-5-2",
                current=False,
            ),
        )
        # create an election that just passed
        PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2021-5-6",
                current=True,
            ),
        )
        response = client.get(past.get_absolute_url(), follow=True)
        assertNotContains(response, "<h3>Next election</h3>")

    @pytest.mark.django_db
    @pytest.mark.freeze_time("2021-5-1")
    def test_next_election_not_displayed_for_current_election(self, client):
        post = PostFactory()
        current = PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2021-5-6",
                current=True,
            ),
        )
        response = client.get(current.get_absolute_url(), follow=True)
        assertNotContains(response, "<h3>Next election</h3>")

    @pytest.mark.django_db
    @pytest.mark.freeze_time("2021-5-6")
    def test_next_election_is_today(self, client):
        post = PostFactory()
        past = PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2019-5-2",
                current=False,
            ),
        )
        # create an election taking place today
        PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2021-5-6",
                current=True,
            ),
        )
        response = client.get(past.get_absolute_url(), follow=True)
        assertContains(response, "<h3>Next election</h3>")
        assertContains(response, "<strong>being held today</strong>.")


class TestPostViewTemplateName:
    @pytest.fixture
    def view_obj(self, rf):
        request = rf.get("/elections/ref.foo.2021-09-01/bar/")
        view = PostView()
        view.setup(request=request)
        return view

    @pytest.mark.parametrize(
        "boolean,template",
        [
            (True, "referendums/detail.html"),
            (False, "elections/post_view.html"),
        ],
    )
    def test_get_template_names(self, boolean, template, view_obj, mocker):
        view_obj.object = mocker.Mock(is_referendum=boolean)
        assert view_obj.get_template_names() == [template]
