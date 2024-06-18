from django.urls import path
from hustings.views import AddHustingView

urlpatterns = [
    path(
        "add/<str:ballot_paper_id>",
        AddHustingView.as_view(),
        name="add-husting",
    ),
]
