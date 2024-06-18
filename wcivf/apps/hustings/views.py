from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.views.generic import CreateView
from elections.models import PostElection
from hustings.forms import AddHustingForm
from hustings.models import Husting


class AddHustingView(CreateView):
    model = Husting
    form_class = AddHustingForm

    def get_initial(self):
        ret = super().get_initial()
        self.ballot = get_object_or_404(
            PostElection, **{"ballot_paper_id": self.kwargs["ballot_paper_id"]}
        )
        ret["post_election"] = self.ballot.pk
        print("called")
        return ret

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["post_election"].initial = self.ballot.pk
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ballot"] = self.ballot
        return context

    def form_valid(self, form):
        form.instance.post_election = self.ballot
        messages.success(
            self.request,
            "Thanks for telling us about this husting. The team will review it.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return self.ballot.get_absolute_url()
