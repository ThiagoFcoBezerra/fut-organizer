from django.db import transaction
from django.utils import timezone
from .models import Attendance, PlayerProfile, Team, TeamMember


@transaction.atomic
def generate_balanced_teams_for_event(event):
    confirmed = list(Attendance.objects.filter(event=event, status="GO").select_related("user"))

    per_team = event.players_per_team_with_gk()
    num_teams = len(confirmed) // per_team
    if num_teams < 2:
        raise ValueError("Jogadores insuficientes para formar pelo menos 2 times.")

    user_ids = [a.user_id for a in confirmed]
    profiles = {
        pp.user_id: pp
        for pp in PlayerProfile.objects.filter(group=event.group, user_id__in=user_ids)
    }

    players = []
    for a in confirmed:
        pp = profiles.get(a.user_id)
        players.append({
            "user": a.user,
            "pp": pp,
            "rating": (pp.rating if pp else 3),
            "position": (pp.position if pp else "MF"),
            "can_be_gk": (pp.can_be_gk if pp else False),
        })

    players_sorted = sorted(players, key=lambda x: x["rating"], reverse=True)
    explicit_gks = [p for p in players_sorted if p["position"] == "GK"]
    voluntary_gks = [p for p in players_sorted if p["position"] != "GK" and p["can_be_gk"]]

    gks = explicit_gks[:num_teams]
    if len(gks) < num_teams:
        gks += voluntary_gks[: (num_teams - len(gks))]
    if len(gks) < num_teams:
        raise ValueError("Não há goleiros suficientes para cada time.")

    Team.objects.filter(event=event).delete()

    teams = [Team.objects.create(event=event, name=f"Time {i+1}") for i in range(num_teams)]
    team_ratings = [0] * num_teams
    team_counts = [0] * num_teams
    allocated = set()

    for i, gk in enumerate(gks):
        idx = i % num_teams
        TeamMember.objects.create(team=teams[idx], user=gk["user"], player_profile=gk["pp"], is_goalkeeper=True)
        team_ratings[idx] += gk["rating"]
        team_counts[idx] += 1
        allocated.add(gk["user"].id)

    remaining = [p for p in players_sorted if p["user"].id not in allocated]
    for p in remaining:
        candidates = [i for i in range(num_teams) if team_counts[i] < per_team]
        if not candidates:
            break
        best = min(candidates, key=lambda i: team_ratings[i])
        TeamMember.objects.create(team=teams[best], user=p["user"], player_profile=p["pp"], is_goalkeeper=False)
        team_ratings[best] += p["rating"]
        team_counts[best] += 1

    for i, t in enumerate(teams):
        t.total_rating = team_ratings[i]
        t.save()

    event.teams_generated_at = timezone.now()
    event.save()

    return teams
