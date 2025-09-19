import random
import time
from typing import Dict, List, Optional

from .core import Song

def auto_tier(
    songs: List[Song],
    n_tiers: int,
    songs_per_tier: int,
    enforce_artist_limit: bool = True,
    keep_very_long_out_of_first_two: bool = True,
    shuffle_seed: Optional[int] = None,
) -> List[List[Song]]:
    """Stratified tiering with randomness within difficulty quantiles."""
    rnd = random.Random(shuffle_seed if shuffle_seed is not None else time.time_ns())
    songs_sorted = sorted(songs, key=lambda s: s.score)
    N = len(songs_sorted)
    if N == 0:
        return [[] for _ in range(n_tiers)]

    def select_with_constraints(ti: int, pool: List[Song], k: int) -> List[Song]:
        picks: List[Song] = []
        artist_counts: Dict[str, int] = {}
        rnd.shuffle(pool)
        for s in pool:
            if len(picks) >= k:
                break
            if keep_very_long_out_of_first_two and ti < 2 and s.is_very_long:
                continue
            if enforce_artist_limit and s.artist and artist_counts.get(s.artist, 0) >= 1:
                continue
            picks.append(s)
            if s.artist:
                artist_counts[s.artist] = artist_counts.get(s.artist, 0) + 1
        return picks

    tiers: List[List[Song]] = [[] for _ in range(n_tiers)]

    for ti in range(n_tiers):
        lo = int(ti * N / n_tiers)
        hi = int((ti + 1) * N / n_tiers)
        bucket = songs_sorted[lo:hi]

        picks = select_with_constraints(ti, bucket.copy(), songs_per_tier)

        expand = 1
        while len(picks) < songs_per_tier and (lo - expand >= 0 or hi + expand <= N):
            left_lo = max(0, lo - expand)
            right_hi = min(N, hi + expand)
            extra = songs_sorted[left_lo:lo] + songs_sorted[hi:right_hi]
            extra = [s for s in extra if s not in picks]
            need = songs_per_tier - len(picks)
            more = select_with_constraints(ti, extra, need)
            for s in more:
                if s not in picks:
                    picks.append(s)
            expand += 1
        tiers[ti] = picks[:songs_per_tier]

    return tiers
