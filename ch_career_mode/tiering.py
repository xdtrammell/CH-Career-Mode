import random
import time
import re
import math
from typing import Dict, List, Optional, Tuple

from .core import Song

GENRE_FAMILY_NAMES = [
    "Metal",
    "Rock",
    "Alternative",
    "Classic Rock",
    "Pop-Rock",
    "Punk",
    "Indie Rock",
    "Pop Rock",
    "Progressive Metal",
    "Alternative Rock",
    "Heavy Metal",
    "Hard Rock",
    "Chiptune",
    "Pop/Dance/Electronic",
    "Thrash Metal",
    "J-Rock",
    "Pop Punk",
    "Country",
    "Electronic",
    "Prog",
    "Grunge",
    "Melodic Death Metal",
    "Metalcore",
    "Nu-Metal",
    "Power Metal",
    "Pop/Rock",
    "Emo",
    "New Wave",
    "Progressive Rock",
    "Punk Rock",
    "Deathcore",
    "Dubstep",
    "Nu Metal",
    "Alternative Metal",
    "Electro",
    "Southern Rock",
    "Game Cover",
    "K-Pop",
    "Other",
]


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


_CANONICAL_FAMILY_LOOKUP: Dict[str, str] = {}
for family_name in GENRE_FAMILY_NAMES:
    key = _normalize_key(family_name)
    if key:
        _CANONICAL_FAMILY_LOOKUP[key] = family_name


def _normalize_genre(genre: str) -> str:
    return _normalize_key(genre)


def _genre_family(genre: str) -> str:
    if not genre:
        return "Other"
    normalized = _normalize_genre(genre)
    if not normalized:
        return "Other"

    if normalized in _CANONICAL_FAMILY_LOOKUP:
        return _CANONICAL_FAMILY_LOOKUP[normalized]

    collapsed = normalized.replace(" ", "")
    best_family = None
    best_key_length = -1
    for key, family in _CANONICAL_FAMILY_LOOKUP.items():
        if family == "Other" or not key:
            continue
        if key in normalized or key.replace(" ", "") in collapsed:
            if len(key) > best_key_length:
                best_key_length = len(key)
                best_family = family

    return best_family or "Other"


def _artist_key(song: Song) -> str:
    return (song.artist or "").strip().lower()


def _tier_sort_key(tier: List[Song], original_index: int) -> Tuple[float, float, float, int]:
    if not tier:
        return (float("inf"), float("inf"), float("inf"), original_index)
    scores = [s.score for s in tier]
    return (min(scores), sum(scores) / len(scores), max(scores), original_index)


def _order_tiers(tiers: List[List[Song]]) -> List[List[Song]]:
    indexed = list(enumerate(tiers))
    indexed.sort(key=lambda item: _tier_sort_key(item[1], item[0]))
    return [tier for _, tier in indexed]


def _compute_score_bands(
    songs_sorted: List[Song],
    n_tiers: int,
) -> Tuple[List[Tuple[float, float, float, float]], float, float]:
    if not songs_sorted:
        return [], 0.0, 0.0

    total = len(songs_sorted)
    global_min = songs_sorted[0].score
    global_max = songs_sorted[-1].score

    bands: List[Tuple[float, float, float, float]] = []
    for ti in range(n_tiers):
        lo = int(ti * total / n_tiers)
        hi = int((ti + 1) * total / n_tiers)
        if hi <= lo:
            hi = min(total, lo + max(1, total // max(1, n_tiers)))
        segment = songs_sorted[lo:hi] or [songs_sorted[min(total - 1, lo)]]
        min_score = segment[0].score
        max_score = segment[-1].score
        median_score = segment[len(segment) // 2].score
        span = max(1.0, max_score - min_score)
        tolerance = max(2.5, span * 0.75)
        bands.append((min_score, median_score, max_score, tolerance))

    return bands, global_min, global_max


def auto_tier(
    songs: List[Song],
    n_tiers: int,
    songs_per_tier: int,
    enforce_artist_limit: bool = True,
    keep_very_long_out_of_first_two: bool = True,
    shuffle_seed: Optional[int] = None,
    group_by_genre: bool = False,
) -> List[List[Song]]:
    rnd = random.Random(shuffle_seed if shuffle_seed is not None else time.time_ns())
    if not songs:
        return [[] for _ in range(n_tiers)]
    if group_by_genre:
        tiers = _auto_tier_by_genre(
            songs,
            n_tiers,
            songs_per_tier,
            enforce_artist_limit,
            keep_very_long_out_of_first_two,
            rnd,
        )
    else:
        tiers = _auto_tier_standard(
            songs,
            n_tiers,
            songs_per_tier,
            enforce_artist_limit,
            keep_very_long_out_of_first_two,
            rnd,
        )
    return _order_tiers(tiers)


def _auto_tier_standard(
    songs: List[Song],
    n_tiers: int,
    songs_per_tier: int,
    enforce_artist_limit: bool,
    keep_very_long_out_of_first_two: bool,
    rnd: random.Random,
) -> List[List[Song]]:
    songs_sorted = sorted(songs, key=lambda s: s.score)
    total = len(songs_sorted)
    tiers: List[List[Song]] = [[] for _ in range(n_tiers)]

    for ti in range(n_tiers):
        lo = int(ti * total / n_tiers)
        hi = int((ti + 1) * total / n_tiers)
        bucket = songs_sorted[lo:hi]
        picks: List[Song] = []
        artist_counts: Dict[str, int] = {}

        def take_from_pool(pool: List[Song]) -> None:
            rnd.shuffle(pool)
            for song in pool:
                if len(picks) >= songs_per_tier:
                    break
                if keep_very_long_out_of_first_two and ti < 2 and song.is_very_long:
                    continue
                if enforce_artist_limit:
                    key = _artist_key(song)
                    if key and artist_counts.get(key, 0) >= 1:
                        continue
                picks.append(song)
                key = _artist_key(song)
                if key:
                    artist_counts[key] = artist_counts.get(key, 0) + 1

        take_from_pool(bucket.copy())

        expand = 1
        while len(picks) < songs_per_tier and (lo - expand >= 0 or hi + expand <= total):
            left_lo = max(0, lo - expand)
            right_hi = min(total, hi + expand)
            extra = songs_sorted[left_lo:lo] + songs_sorted[hi:right_hi]
            extra = [s for s in extra if s not in picks]
            need = songs_per_tier - len(picks)
            take_from_pool(extra[:need * 4])
            expand += 1
        tiers[ti] = sorted(picks[:songs_per_tier], key=lambda s: (s.score, s.name.lower()))

    return tiers


def _build_family_plan(
    families: Dict[str, List[Song]],
    n_tiers: int,
    rnd: random.Random,
) -> List[str]:
    present = {fam: len(pool) for fam, pool in families.items() if pool}
    if not present or n_tiers <= 0:
        return []

    total_songs = sum(present.values())
    quotas: Dict[str, int] = {}
    remainders: List[Tuple[float, int, float, str]] = []
    for fam, count in present.items():
        share = (count / total_songs) * n_tiers if total_songs else 0.0
        base = int(math.floor(share))
        quotas[fam] = base
        remainders.append((share - base, count, rnd.random(), fam))

    assigned = sum(quotas.values())
    leftover = n_tiers - assigned
    if leftover > 0 and remainders:
        remainders.sort(reverse=True)
        idx = 0
        while leftover > 0:
            fam = remainders[idx % len(remainders)][3]
            quotas[fam] = quotas.get(fam, 0) + 1
            leftover -= 1
            idx += 1

    diversity_target = min(len(present), max(1, math.ceil(n_tiers / 3)))

    def _families_with_allocation() -> int:
        return sum(1 for qty in quotas.values() if qty > 0)

    while _families_with_allocation() < diversity_target:
        zero_candidates = [fam for fam in present if quotas.get(fam, 0) == 0]
        donor_candidates = [fam for fam, qty in quotas.items() if qty > 1]
        if not zero_candidates or not donor_candidates:
            break
        zero_candidates.sort(key=lambda fam: (present[fam], rnd.random()), reverse=True)
        donor_candidates.sort(key=lambda fam: (quotas[fam], present[fam], rnd.random()), reverse=True)
        donor = donor_candidates[0]
        recipient = zero_candidates[0]
        quotas[donor] -= 1
        quotas[recipient] = quotas.get(recipient, 0) + 1

    if quotas:
        majority_family = max(present, key=lambda fam: present[fam])
        minority_families = [fam for fam in present if fam != majority_family]
        if minority_families:
            target_minority_tiers = min(n_tiers, max(1, math.ceil(n_tiers / 3)))
            current_minority_tiers = sum(quotas.get(fam, 0) for fam in minority_families)
            max_majority_tiers = max(0, n_tiers - target_minority_tiers)
            while current_minority_tiers < target_minority_tiers and quotas.get(majority_family, 0) > max_majority_tiers:
                recipient_candidates = sorted(
                    minority_families,
                    key=lambda fam: (quotas.get(fam, 0), -present[fam], rnd.random()),
                )
                if not recipient_candidates:
                    break
                recipient = recipient_candidates[0]
                quotas[majority_family] -= 1
                quotas[recipient] = quotas.get(recipient, 0) + 1
                current_minority_tiers += 1

    plan: List[str] = []
    for fam, qty in quotas.items():
        plan.extend([fam] * qty)

    if len(plan) < n_tiers:
        filler = sorted(present.keys(), key=lambda fam: (present[fam], rnd.random()), reverse=True)
        idx = 0
        while len(plan) < n_tiers and filler:
            plan.append(filler[idx % len(filler)])
            idx += 1

    rnd.shuffle(plan)
    if len(plan) > n_tiers:
        plan = plan[:n_tiers]

    return plan


def _auto_tier_by_genre(
    songs: List[Song],
    n_tiers: int,
    songs_per_tier: int,
    enforce_artist_limit: bool,
    keep_very_long_out_of_first_two: bool,
    rnd: random.Random,
) -> List[List[Song]]:
    songs_sorted_global = sorted(songs, key=lambda s: (s.score, s.name.lower()))
    bands, global_min_score, global_max_score = _compute_score_bands(songs_sorted_global, n_tiers)
    global_span = max(1.0, global_max_score - global_min_score)

    families: Dict[str, List[Song]] = {}
    for song in songs_sorted_global:
        families.setdefault(_genre_family(song.genre), []).append(song)

    plan = _build_family_plan(families, n_tiers, rnd)
    if not plan:
        return [[] for _ in range(n_tiers)]

    for pool in families.values():
        pool.sort(key=lambda song: (song.score, song.name.lower()))

    family_tiers_remaining: Dict[str, int] = {fam: plan.count(fam) for fam in families}

    tiers: List[List[Song]] = [[] for _ in range(n_tiers)]

    def _family_candidates(pool: List[Song], min_score: float, max_score: float) -> List[Song]:
        matches: List[Song] = []
        for song in pool:
            if song.score < min_score:
                continue
            if song.score > max_score:
                break
            matches.append(song)
        return matches

    for ti in range(n_tiers):
        picks: List[Song] = []
        artist_counts: Dict[str, int] = {}

        primary_family = plan[ti] if ti < len(plan) else max(families, key=lambda fam: len(families[fam]))
        remaining = family_tiers_remaining.get(primary_family, 0)
        if remaining > 0:
            family_tiers_remaining[primary_family] = remaining - 1

        if bands:
            band_index = min(ti, len(bands) - 1)
            band_min, _, band_max, band_tolerance = bands[band_index]
        else:
            band_min = global_min_score
            band_max = global_max_score
            band_tolerance = max(2.5, global_span)

        expansion = 0.0
        expansion_step = max(2.5, band_tolerance)
        max_expansion = max(global_span, band_tolerance * 4.0)
        final_expansion = max_expansion * 2.0

        def take_from_family(family: str, allow_artist_limit: bool, score_expansion: float) -> bool:
            pool = families.get(family)
            if not pool:
                return False
            min_allowed = max(global_min_score, band_min - score_expansion)
            max_allowed = min(global_max_score, band_max + score_expansion)
            if min_allowed > max_allowed:
                min_allowed, max_allowed = max_allowed, min_allowed
            candidates = _family_candidates(pool, min_allowed, max_allowed)
            if not candidates:
                return False
            rnd.shuffle(candidates)
            picked_any = False
            for song in candidates:
                if len(picks) >= songs_per_tier:
                    break
                if keep_very_long_out_of_first_two and ti < 2 and song.is_very_long:
                    continue
                key = _artist_key(song)
                if allow_artist_limit and enforce_artist_limit and key and artist_counts.get(key, 0) >= 1:
                    continue
                pool.remove(song)
                picks.append(song)
                if key:
                    artist_counts[key] = artist_counts.get(key, 0) + 1
                picked_any = True
            return picked_any

        def fallback_families() -> List[str]:
            others = [fam for fam, pool in families.items() if fam != primary_family and pool]
            others.sort(
                key=lambda fam: (
                    len(families[fam]) - family_tiers_remaining.get(fam, 0) * songs_per_tier,
                    len(families[fam]),
                    rnd.random(),
                ),
                reverse=True,
            )
            return others

        while len(picks) < songs_per_tier:
            progress = False

            if take_from_family(primary_family, True, expansion):
                progress = True
            if len(picks) >= songs_per_tier:
                break

            if not progress:
                for fam in fallback_families():
                    if take_from_family(fam, True, expansion):
                        progress = True
                    if len(picks) >= songs_per_tier:
                        break
            if len(picks) >= songs_per_tier:
                break

            if not progress and take_from_family(primary_family, False, expansion):
                progress = True
            if len(picks) >= songs_per_tier:
                break

            if not progress:
                for fam in fallback_families():
                    if take_from_family(fam, False, expansion):
                        progress = True
                    if len(picks) >= songs_per_tier:
                        break
            if len(picks) >= songs_per_tier:
                break

            if progress:
                continue

            if expansion >= max_expansion:
                for fam, pool in families.items():
                    if not pool:
                        continue
                    take_from_family(fam, False, final_expansion)
                    if len(picks) >= songs_per_tier:
                        break
                break

            expansion = min(max_expansion, expansion + expansion_step)

        tiers[ti] = sorted(picks[:songs_per_tier], key=lambda s: (s.score, s.name.lower()))

    return tiers
