# Generated by Django 3.2.12 on 2022-04-12 12:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("parties", "0012_add_youtube_and_contact_url"),
        ("people", "0041_dummycandidacy_dummyperson"),
    ]

    operations = [
        migrations.AddField(
            model_name="personpost",
            name="previous_party_affiliations",
            field=models.ManyToManyField(
                blank=True,
                related_name="affiliated_memberships",
                to="parties.Party",
            ),
        ),
    ]
