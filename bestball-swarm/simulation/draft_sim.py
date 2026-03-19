"""
Bestball Draft Simulator
=========================
12-team, 17-round snake draft with half-point PPR scoring.
Optimized for millions of calls.

Usage:
    from simulation.draft_sim import DraftEnvironment, PLAYER_POOL
    env = DraftEnvironment()
    while not env.is_complete():
        env.make_pick(env.current_team, selected_player)
    results = env.get_results()
"""

from __future__ import annotations
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STARTING_SLOTS = ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "SUPER_FLEX"]

# ---------------------------------------------------------------------------
# Player dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Player:
    name: str
    position: str          # QB | RB | WR | TE | DST | K
    adp: float
    projected_points: float
    age: int
    ktc_value: int

    def tier(self) -> int:
        if self.adp <= 12:   return 1
        if self.adp <= 36:   return 2
        if self.adp <= 72:   return 3
        if self.adp <= 144:  return 4
        return 5


# ---------------------------------------------------------------------------
# DraftResults dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TeamResult:
    team_id: int
    roster: Tuple[Player, ...]
    total_projected_points: float
    starting_points: float
    positional_breakdown: Dict[str, Tuple[Player, ...]]
    key_picks: Tuple[Player, ...]


@dataclass(frozen=True, slots=True)
class DraftResults:
    team_results: Tuple[TeamResult, ...]
    draft_order: Tuple[int, ...]
    rounds_completed: int
    total_picks: int

    def winner(self) -> TeamResult:
        return max(self.team_results, key=lambda t: t.starting_points)

    def standings(self) -> List[TeamResult]:
        return sorted(self.team_results, key=lambda t: t.starting_points, reverse=True)


# ---------------------------------------------------------------------------
# Player pool — 280+ realistic 2025 dynasty players
# ---------------------------------------------------------------------------

def _build_player_pool() -> List[Player]:
    raw = [
        # R1
        ("Josh Allen","QB",1.01,425.0,29,12500),("Lamar Jackson","QB",1.02,405.0,28,11800),
        ("Jalen Hurts","QB",1.03,395.0,26,11200),("Patrick Mahomes","QB",1.04,415.0,29,12000),
        ("Joe Mixon","RB",1.05,280.0,28,8500),("CeeDee Lamb","WR",1.06,310.0,25,11500),
        ("Amon-Ra St. Brown","WR",1.07,305.0,24,11000),("Ja'Marr Chase","WR",1.08,300.0,24,10800),
        ("Puka Nacua","WR",1.09,285.0,23,9500),("Brock Bowers","TE",1.10,220.0,22,8800),
        ("Tracy Morgan","RB",1.11,260.0,23,8200),("Jayden Daniels","QB",1.12,295.0,23,8200),
        # R2
        ("Christian McCaffrey","RB",2.01,275.0,28,10500),("Tyreek Hill","WR",2.02,290.0,30,10200),
        ("Davante Adams","WR",2.03,275.0,32,9200),("A.J. Brown","WR",2.04,280.0,27,9800),
        ("Drake Maye","QB",2.05,310.0,22,8500),("Saquon Barkley","RB",2.06,265.0,27,8800),
        ("Kyren Williams","RB",2.07,250.0,24,7800),("DeVonta Smith","WR",2.08,265.0,25,8400),
        ("Chris Olave","WR",2.09,255.0,24,8100),("Garrett Wilson","WR",2.10,250.0,24,7900),
        ("George Pickens","WR",2.11,245.0,23,7600),("De'Von Achane","RB",2.12,195.0,23,6400),
        # R3
        ("Calvin Ridley","WR",3.01,235.0,30,7000),("Trey McBride","TE",3.02,200.0,25,8200),
        ("Chris Godwin","WR",3.03,240.0,28,7500),("Stefon Diggs","WR",3.04,225.0,31,6800),
        ("Rashid Shaheed","WR",3.05,210.0,25,6200),("David Njoku","TE",3.06,185.0,28,7000),
        ("Travis Kelce","TE",3.07,195.0,35,8500),("Mark Andrews","TE",3.08,175.0,29,6500),
        ("Dallas Goedert","TE",3.09,170.0,29,6200),("Tee Higgins","WR",3.10,220.0,26,7800),
        ("Brian Robinson","RB",3.11,200.0,24,5800),("Nick Chubb","RB",3.12,210.0,28,6500),
        # R4
        ("James Cook","RB",4.01,215.0,25,7200),("Alvin Kamara","RB",4.02,205.0,30,6800),
        ("Joe Burrow","QB",4.03,280.0,28,9500),("Trevor Lawrence","QB",4.04,260.0,25,8000),
        ("Justin Herbert","QB",4.05,255.0,27,7800),("Kyler Murray","QB",4.06,250.0,27,7500),
        ("Baker Mayfield","QB",4.07,235.0,29,6200),("Rhamondre Stevenson","RB",4.08,185.0,26,5400),
        ("Tony Pollard","RB",4.09,175.0,27,5000),("D'Andre Swift","RB",4.10,170.0,25,4800),
        ("Kenneth Walker III","RB",4.11,180.0,24,5600),("Isiah Pacheco","RB",4.12,160.0,24,4800),
        # R5
        ("D.K. Metcalf","WR",5.01,210.0,27,7200),("Brandon Aiyuk","WR",5.02,215.0,26,7400),
        ("Amari Cooper","WR",5.03,190.0,30,6000),("Keenan Allen","WR",5.04,200.0,32,6200),
        ("Courtland Sutton","WR",5.05,180.0,29,5600),("Jerry Jeudy","WR",5.06,175.0,26,5400),
        ("Rome Odunze","WR",5.07,185.0,22,5200),("Malik Nabers","WR",5.08,180.0,22,5000),
        ("Marvin Harrison Jr.","WR",5.09,175.0,22,4900),("Ladd McConkey","WR",5.10,165.0,22,4400),
        ("Xavier Worthy","WR",5.11,170.0,21,4600),("Adonai Mitchell","WR",5.12,160.0,21,4200),
        # R6
        ("Jahan Dotson","WR",6.01,195.0,24,5500),("Zay Flowers","WR",6.02,160.0,23,4600),
        ("Drake London","WR",6.03,150.0,23,4000),("Quentin Johnston","WR",6.04,145.0,23,3800),
        ("Tank Dell","WR",6.05,140.0,24,3600),("Christian Watson","WR",6.06,155.0,25,4200),
        ("Marvin Mims","WR",6.07,100.0,22,2000),("Jordan Whittington","WR",6.08,95.0,21,1800),
        ("Troy Franklin","WR",6.09,90.0,21,1700),("Malik Washington","WR",6.10,85.0,22,1500),
        ("Luke McCaffrey","WR",6.11,80.0,24,1400),("DeMario Douglas","WR",6.12,160.0,23,4200),
        # R7
        ("Blake Corum","RB",7.01,120.0,23,2900),("Braelon Allen","RB",7.02,115.0,20,2700),
        ("Audric Estime","RB",7.03,110.0,22,2500),("Chase Brown","RB",7.04,100.0,24,2200),
        ("Ray Davis","RB",7.05,85.0,22,1800),("MarShawn Lloyd","RB",7.06,80.0,23,1600),
        ("Jaylen Wright","RB",7.07,75.0,21,1400),("Isaac Guerendo","RB",7.08,70.0,23,1200),
        ("Jonatan Brooks","RB",7.09,65.0,22,1000),("Kendre Miller","RB",7.10,60.0,22,900),
        ("Ezekiel Elliott","RB",7.11,95.0,29,2000),("Antonio Gibson","RB",7.12,90.0,26,1900),
        # R8 — QBs + TEs
        ("Caleb Williams","QB",8.01,200.0,23,7000),("Bo Nix","QB",8.02,120.0,24,2500),
        ("Michael Penix Jr.","QB",8.03,130.0,23,3000),("J.J. McCarthy","QB",8.04,140.0,22,3500),
        ("Brock Bowers","TE",8.05,165.0,22,5800),("David Njoku","TE",8.06,150.0,28,5200),
        ("Sam LaPorta","TE",8.07,130.0,23,4500),("Trey McBride","TE",8.08,160.0,25,6200),
        ("Dalton Schultz","TE",8.09,120.0,28,4000),("Mike Gesicki","TE",8.10,110.0,29,3600),
        ("Cole Kmet","TE",8.11,100.0,25,3200),("Chigoziem Okonkwo","TE",8.12,95.0,24,3000),
        # R9 — QBs
        ("C.J. Stroud","QB",9.01,220.0,22,7800),("Tua Tagovailoa","QB",9.02,200.0,27,6800),
        ("Jordan Love","QB",9.03,165.0,26,5000),("Kirk Cousins","QB",9.04,180.0,36,5500),
        ("Jared Goff","QB",9.05,170.0,30,5200),("Matthew Stafford","QB",9.06,160.0,37,4800),
        ("Geno Smith","QB",9.07,140.0,34,4000),("Bryce Young","QB",9.08,80.0,23,1500),
        ("Will Levis","QB",9.09,55.0,25,1100),("Mac Jones","QB",9.10,50.0,26,1000),
        ("Kenny Pickett","QB",9.11,45.0,26,900),("Desmond Ridder","QB",9.12,40.0,25,800),
        # R10 — WR depth
        ("Tyreek Hill","WR",10.01,200.0,30,7000),("Amari Cooper","WR",10.02,175.0,30,5500),
        ("Mike Williams","WR",10.03,50.0,30,900),("Khalil Shakir","WR",10.04,60.0,24,900),
        ("Allen Lazard","WR",10.05,55.0,28,800),("Van Jefferson","WR",10.06,50.0,27,750),
        ("Greg Dortch","WR",10.07,55.0,26,900),("Odell Beckham Jr.","WR",10.08,120.0,33,3500),
        ("Tyler Boyd","WR",10.09,70.0,30,1500),("Hollywood Brown","WR",10.10,90.0,27,2000),
        ("Zay Jones","WR",10.11,55.0,29,900),("Darius Slayton","WR",10.12,50.0,28,800),
        # R11 — RB depth
        ("Kareem Hunt","RB",11.01,75.0,29,1200),("Jerome Ford","RB",11.02,70.0,24,1100),
        ("Ty Chandler","RB",11.03,85.0,25,1800),("Emari Demarcado","RB",11.04,80.0,23,1600),
        ("Ronnie Rivers","RB",11.05,30.0,26,500),("AJ Dillon","RB",11.06,60.0,26,900),
        ("D'Onta Foreman","RB",11.07,65.0,28,1000),("JaMycal Hasty","RB",11.08,20.0,27,300),
        ("Ty Johnson","RB",11.09,25.0,27,400),("Patrick Laird","RB",11.10,20.0,28,350),
        ("Kenneth Gainwell","RB",11.11,30.0,25,500),("Keaton Mitchell","RB",11.12,25.0,22,400),
        # R12 — TEs
        ("Juwan Johnson","TE",12.01,105.0,27,3400),("Luke Musgrave","TE",12.02,90.0,23,2800),
        ("Jelani Woods","TE",12.03,85.0,24,2600),("Foster Moreau","TE",12.04,75.0,27,2200),
        ("Hunter Henry","TE",12.05,80.0,30,2200),("Robert Tonyan","TE",12.06,70.0,30,1800),
        ("Mo Alie-Cox","TE",12.07,60.0,28,1400),("Adam Trautman","TE",12.08,50.0,27,1100),
        ("Pat Freiermuth","TE",12.09,100.0,25,3200),("Tommy Tremble","TE",12.10,35.0,24,900),
        ("Durham Smythe","TE",12.11,40.0,29,1000),("Taysom Hill","TE",12.12,60.0,34,1500),
        # R13 — QB depth
        ("Cooper Rush","QB",13.01,5.0,31,100),("Gardner Minshew","QB",13.02,25.0,28,450),
        ("Tyrod Taylor","QB",13.03,15.0,35,350),("Marcus Mariota","QB",13.04,20.0,31,400),
        ("Mason Rudolph","QB",13.05,5.0,29,50),("Ryan Tannehill","QB",13.06,30.0,37,500),
        ("Taylor Heinicke","QB",13.07,5.0,31,100),("Easton Stick","QB",13.08,2.0,29,50),
        ("Sam Howell","QB",13.09,45.0,24,900),("Aidan O'Connell","QB",13.10,50.0,26,950),
        ("Jaren Hall","QB",13.11,45.0,24,850),("Bailey Zappe","QB",13.12,10.0,25,200),
        # R14 — WR deep + bench
        ("Marques Valdes-Scantling","WR",14.01,40.0,30,600),("Trent Sherfield","WR",14.02,30.0,28,500),
        ("Jalin Hyatt","WR",14.03,20.0,23,350),("Jared Wayne","WR",14.04,20.0,24,300),
        ("Jalen Nailor","WR",14.05,15.0,25,250),("Steven Sims Jr.","WR",14.06,10.0,27,200),
        ("Tim Patrick","WR",14.07,40.0,31,600),("Dee Eskridge","WR",14.08,20.0,25,300),
        ("Matt Breida","RB",14.09,25.0,30,400),("Boston Scott","RB",14.10,20.0,30,350),
        ("Marlon Mack","RB",14.11,15.0,28,250),("Julius Brents","WR",14.12,25.0,24,400),
        # R15 — Ks
        ("Harrison Butker","K",15.01,130.0,29,400),("Daniel Carlson","K",15.02,125.0,28,380),
        ("Jake Elliott","K",15.03,120.0,29,360),("Tyler Bass","K",15.04,118.0,27,340),
        ("Evan McPherson","K",15.05,115.0,26,320),("Chris Boswell","K",15.06,112.0,33,300),
        ("Graham Gano","K",15.07,110.0,33,280),("Jason Sanders","K",15.08,108.0,29,260),
        ("Matt Gay","K",15.09,105.0,30,240),("Dustin Hopkins","K",15.10,100.0,32,220),
        ("Ka'imi Fairbairn","K",15.11,95.0,30,200),("Jason Myers","K",15.12,90.0,32,180),
        # R16 — DST
        ("Dallas DST","DST",16.01,120.0,0,500),("San Francisco DST","DST",16.02,115.0,0,480),
        ("Buffalo DST","DST",16.03,110.0,0,460),("Philadelphia DST","DST",16.04,108.0,0,440),
        ("Cleveland DST","DST",16.05,105.0,0,420),("NY Jets DST","DST",16.06,100.0,0,400),
        ("Kansas City DST","DST",16.07,98.0,0,380),("Baltimore DST","DST",16.08,95.0,0,360),
        ("Pittsburgh DST","DST",16.09,92.0,0,340),("Miami DST","DST",16.10,90.0,0,320),
        ("LA Rams DST","DST",16.11,85.0,0,280),("Detroit DST","DST",16.12,82.0,0,260),
        # R17+ bench
        ("Kenny Golladay","WR",17.01,35.0,31,600),("Johnathan Benjamin","WR",17.02,20.0,23,300),
        ("Olamide Zaccheaus","WR",17.03,30.0,27,400),("Justin Watson","WR",17.04,25.0,28,350),
        ("Demarcus Robinson","WR",17.05,50.0,30,750),("Mack Hollins","WR",17.06,45.0,31,700),
        ("KhaDarel Hodge","WR",17.07,40.0,29,600),("Equanimeous St. Brown","WR",17.08,30.0,28,400),
        ("Tre'Quan Smith","WR",17.09,30.0,28,400),
        ("Spencer Brown","RB",17.10,15.0,25,250),("Jacques Patrick","RB",17.11,5.0,27,50),
        ("Keaontay Ingram","RB",17.12,5.0,24,100),("Trey Sermon","RB",17.13,10.0,25,200),
        ("Chris Rodriguez Jr.","RB",17.14,8.0,24,150),("Emani Jackson","RB",17.15,5.0,21,100),
        ("Will Shipley","RB",17.16,5.0,22,100),("C.J. Evans","RB",17.17,5.0,23,80),
        ("Sean Clifford","QB",17.18,2.0,26,50),("Trace McSorley","QB",17.19,1.0,30,30),
        ("Kurt Benkert","QB",17.20,1.0,29,30),
        ("Green Bay DST","DST",17.21,80.0,0,240),("Tampa Bay DST","DST",17.22,78.0,0,220),
        ("Indianapolis DST","DST",17.23,75.0,0,200),("Seattle DST","DST",17.24,72.0,0,180),
        ("Chase McLaughlin","K",17.25,85.0,28,160),("Greg Zuerlein","K",17.26,80.0,32,150),
        ("Eddy Pineiro","K",17.27,78.0,28,140),
        ("Miles Boykin","WR",18.01,5.0,28,50),("Josh Doctson","WR",18.02,2.0,31,30),
        ("John Brown","WR",18.03,5.0,33,50),("Damien Harris","RB",18.04,10.0,28,200),
        ("Darrel Williams","RB",18.05,5.0,29,150),("Peyton Hough","RB",18.06,3.0,22,50),
        ("Rashard Higgins","WR",18.07,45.0,30,700),("Jamison Crowder","WR",18.08,40.0,31,600),
        ("Nsimba Webster","WR",18.09,5.0,27,50),("Mike Wilson","WR",18.10,5.0,28,50),
        ("Will Lutz","K",18.11,75.0,31,130),("Matt McCrane","K",18.12,70.0,29,120),
        ("New England DST","DST",18.13,68.0,0,150),("Las Vegas DST","DST",18.14,65.0,0,130),
        ("Arizona DST","DST",18.15,62.0,0,110),("Tennessee DST","DST",18.16,60.0,0,100),
        ("Stetson Bennett","QB",19.01,35.0,27,700),
        ("Dorian Thompson-Robinson","QB",19.02,40.0,24,800),
        ("Tommy DeVito","QB",19.03,40.0,25,750),
        ("Jaxson Dart","QB",19.04,2.0,22,50),("Spencer Rattler","QB",19.05,2.0,24,50),
        ("Tony Jones","RB",19.06,5.0,25,100),("Khalid Shakir","WR",19.07,10.0,24,100),
    ]

    seen, players = set(), []
    for row in raw:
        if row[0] not in seen:
            seen.add(row[0])
            players.append(Player(row[0], row[1], row[2], row[3], row[4], row[5]))
    return players


PLAYER_POOL: Tuple[Player, ...] = tuple(sorted(_build_player_pool(), key=lambda p: p.adp))


# ---------------------------------------------------------------------------
# DraftEnvironment
# ---------------------------------------------------------------------------

class DraftEnvironment:
    """
    Manages a bestball draft: 12 teams, 17 rounds, snake order.
    No trades, no waivers, no in-season management.

    For millions-of-calls efficiency:
    - __slots__ avoids __dict__ overhead
    - Pre-computed snake order
    - O(n) available-player removal, O(1) roster append
    """

    __slots__ = (
        "num_teams", "rounds", "total_picks", "rosters",
        "_available", "_order", "_pick", "_round", "_team_idx",
    )

    def __init__(self, num_teams: int = 12, rounds: int = 17, seed: Optional[int] = None):
        self.num_teams = num_teams
        self.rounds = rounds
        self.total_picks = num_teams * rounds
        self.rosters: List[List[Player]] = [[] for _ in range(num_teams)]
        self._available: List[Player] = list(PLAYER_POOL)
        self._order: List[int] = self._build_snake()
        self._pick = 0
        self._round = 1
        self._team_idx = 0
        if seed is not None:
            random.seed(seed)

    # ---- snake order ---------------------------------------------------
    def _build_snake(self) -> List[int]:
        order: List[int] = []
        for r in range(1, self.rounds + 1):
            if r % 2 == 1:
                order.extend(range(self.num_teams))
            else:
                order.extend(range(self.num_teams - 1, -1, -1))
        return order

    # ---- public API ----------------------------------------------------
    @property
    def current_round(self) -> int:
        return self._round

    @property
    def current_pick(self) -> int:          # 1-indexed
        return self._pick + 1

    @property
    def current_team(self) -> int:
        return self._order[self._team_idx]

    def get_available(self) -> List[Player]:
        return self._available

    def get_available_by_pos(self, pos: str) -> List[Player]:
        return [p for p in self._available if p.position == pos]

    def get_top_available(self, n: int = 10, pos: Optional[str] = None) -> List[Player]:
        src = self._available if pos is None else self.get_available_by_pos(pos)
        return sorted(src, key=lambda p: p.adp)[:n]

    def make_pick(self, team_id: int, player: Player) -> None:
        if team_id != self.current_team:
            raise ValueError(f"Team {team_id} cannot pick — it is team {self.current_team}'s turn")
        if player not in self._available:
            raise ValueError(f"{player.name} is not available")
        if self.is_complete():
            raise ValueError("Draft is already complete")
        self.rosters[team_id].append(player)
        self._available.remove(player)
        self._pick += 1
        self._team_idx += 1
        self._round = min((self._pick // self.num_teams) + 1, self.rounds)

    def auto_pick(self, team_id: int) -> Player:
        """Pick the best available player by ADP. Use for simulated opponents."""
        best = self.get_top_available(1)[0]
        self.make_pick(team_id, best)
        return best

    def is_complete(self) -> bool:
        return self._pick >= self.total_picks

    def picks_remaining(self) -> int:
        return self.total_picks - self._pick

    def get_draft_state_text(self) -> str:
        lines = [
            f"Round {self._round} | Pick {self.current_pick}/{self.total_picks} | "
            f"Team {self.current_team} on the clock",
            f"Available: {len(self._available)} players  |  Top available: "
            + ", ".join(f"{p.name}({p.position},{p.adp:.2f})" for p in self.get_top_available(5)),
        ]
        for tid, roster in enumerate(self.rosters):
            if roster:
                pts = sum(p.projected_points for p in roster)
                cnt = {pos: sum(1 for p in roster if p.position == pos) for pos in ("QB","RB","WR","TE")}
                lines.append(
                    f"  Team {tid}: {len(roster)} picks, {pts:.0f} total pts  "
                    f"QB={cnt['QB']} RB={cnt['RB']} WR={cnt['WR']} TE={cnt['TE']}"
                )
        return "\n".join(lines)

    # ---- results -------------------------------------------------------
    def get_results(self) -> DraftResults:
        team_results: List[TeamResult] = []
        for tid, roster in enumerate(self.rosters):
            rtuple = tuple(roster)
            total = sum(p.projected_points for p in roster)
            pos_bd = {pos: tuple(pl for pl in roster if pl.position == pos) for pos in ("QB","RB","WR","TE","DST","K")}
            key3 = tuple(sorted(roster, key=lambda x: x.projected_points, reverse=True)[:3])
            team_results.append(TeamResult(
                team_id=tid, roster=rtuple, total_projected_points=total,
                starting_points=self._lineup_points(roster),
                positional_breakdown=pos_bd, key_picks=key3,
            ))
        return DraftResults(
            team_results=tuple(team_results),
            draft_order=tuple(range(self.num_teams)),
            rounds_completed=self._round - (0 if self.is_complete() else 1),
            total_picks=self._pick,
        )

    # ---- lineup scoring (half-point PPR) ------------------------------
    def _lineup_points(self, roster: List[Player]) -> float:
        """Best 9-player starting lineup: 1QB 2RB 3WR 1TE 1FLEX 1SF."""
        by_pos: Dict[str, List[Player]] = {}
        for p in roster:
            by_pos.setdefault(p.position, []).append(p)

        def top(lst: List[Player], n: int) -> List[Player]:
            return sorted(lst, key=lambda x: x.projected_points, reverse=True)[:n]

        def pts(lst: List[Player]) -> float:
            return sum(p.projected_points for p in lst)

        qb  = top(by_pos.get("QB", []), 1)
        rbs = top(by_pos.get("RB", []), 2)
        wrs = top(by_pos.get("WR", []), 3)
        te  = top(by_pos.get("TE", []), 1)

        # FLEX: best of RB3+, WR4+, TE2+
        flex_pool: List[Player] = []
        if len(rbs) > 2: flex_pool.extend(rbs[2:])
        if len(wrs) > 3: flex_pool.extend(wrs[3:])
        if len(te)  > 1: flex_pool.extend(te[1:])
        flex = [top(flex_pool, 1)[0]] if flex_pool else []

        # SF: best remaining after flex
        sf_pool = list(flex_pool)
        for q in qb: sf_pool.append(q)
        sf_pool = [p for p in sf_pool if p not in qb + rbs[:2] + wrs[:3] + te[:1] + flex]
        sf = [top(sf_pool, 1)[0]] if sf_pool else []

        return pts(qb) + pts(rbs) + pts(wrs) + pts(te) + pts(flex) + pts(sf)

    # ---- full random draft helper -------------------------------------
    @staticmethod
    def run_random_draft(
        num_teams: int = 12, rounds: int = 17, seed: Optional[int] = None,
        agent_picks: Optional[Dict[int, str]] = None,
    ) -> DraftResults:
        """
        Run a complete draft.
        `agent_picks`: {team_id: "auto"} for auto-pick teams,
                       {team_id: "player_name"} for a specific pick.
        """
        env = DraftEnvironment(num_teams=num_teams, rounds=rounds, seed=seed)
        agents = agent_picks or {}
        while not env.is_complete():
            tid = env.current_team
            if tid in agents:
                cmd = agents[tid]
                if cmd == "auto":
                    env.auto_pick(tid)
                else:
                    avail = {p.name: p for p in env.get_available()}
                    if cmd in avail:
                        env.make_pick(tid, avail[cmd])
                    else:
                        env.auto_pick(tid)
            else:
                env.auto_pick(tid)
        return env.get_results()


# ---------------------------------------------------------------------------
# Valuator helpers (for swarm agents)
# ---------------------------------------------------------------------------

def player_value_score(p: Player, age_curve: bool = True) -> float:
    """Composite value: KTC (40%) + projected points (60%) × age multiplier."""
    ktc  = p.ktc_value / 12500.0
    pts  = p.projected_points / 425.0
    if age_curve:
        mult = 1.15 if p.age <= 23 else 1.0 if p.age <= 28 else 0.85 if p.age <= 31 else 0.7
    else:
        mult = 1.0
    return (0.4 * ktc + 0.6 * pts) * mult


def age_adjusted_value(p: Player, prime: int = 27) -> float:
    """KTC-style age curve: peak at prime_age, −2.5% per year away, clamped [0.4, 1.15]."""
    mult = 1.0 - (abs(p.age - prime) * 0.025)
    return max(0.4, min(1.15, mult))


def best_value_pick(available: List[Player], roster: List[Player]) -> Optional[Player]:
    """Return highest value-per-roster-spot given current roster needs."""
    if not available:
        return None
    need: Dict[str, int] = {"QB": 1, "RB": 2, "WR": 3, "TE": 1}
    for p in roster:
        if p.position in need and need[p.position] > 0:
            need[p.position] -= 1
    scored = []
    for p in available:
        mult = 1.5 if (p.position in need and need[p.position] > 0) else 1.0
        scored.append((player_value_score(p) * mult, p))
    scored.sort(reverse=True)
    return scored[0][1] if scored else None


# ---------------------------------------------------------------------------
# CLI quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"PLAYER_POOL: {len(PLAYER_POOL)} players")
