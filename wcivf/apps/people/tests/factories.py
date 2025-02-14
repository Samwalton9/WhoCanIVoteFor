import factory
from parties.tests.factories import PartyFactory

from people.models import Person, PersonPost
from elections.tests.factories import (
    ElectionFactory,
    PostFactory,
    PostElectionFactory,
)


class PersonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Person

    ynr_id = factory.Sequence(lambda n: n)
    name = factory.Sequence(lambda n: "Candidate %d" % n)
    elections = factory.RelatedFactory(ElectionFactory)


class PersonPostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PersonPost

    person = factory.SubFactory(PersonFactory)
    post = factory.SubFactory(PostFactory)
    post_election = factory.SubFactory(PostElectionFactory)
    party = None
    list_position = None


class PersonPostWithPartyFactory(PersonPostFactory):

    party = factory.SubFactory(PartyFactory)

    @factory.lazy_attribute
    def party_name(self):
        return self.party.party_name
