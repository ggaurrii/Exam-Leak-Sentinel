"""
synthetic_feed.py

Generates candidate content items for demo/dev purposes so the system can
be exercised without real scraping. Mixes:
  - clean/unrelated posts (should classify Low, most of the volume)
  - partial matches (paraphrased or partial reproduction of a reference
    question — should generally land Medium, sometimes High depending on
    how distinctive the reproduced fragment is)
  - near-exact leaks (near-verbatim reproduction of a reference question
    and/or its answer options — should land High)

This module ONLY produces candidate_text + source_feed + a debug label of
its intended category (intended_category is for eyeballing/demo narration
only — it is NEVER passed to the matching engine or used to influence the
Bedrock calls in any way; the whole point is that Bedrock scores these
blind).
"""

import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

SOURCE_FEEDS = [
    "Public Feed A",
    "Public Feed B",
    "Institutional Feed",
    "Authorized Feed",
]

_CLEAN_FILLER = [
    "Anyone know a good place to eat near the exam center tomorrow?",
    "Good luck everyone taking the exam this weekend!",
    "Does the exam hall allow water bottles?",
    "Reminder: bring your admit card and a valid photo ID.",
    "What time do doors open for the morning session?",
    "Is there parking available near the test center?",
    "Can I bring a calculator for the exam?",
    "Weather looks rainy on exam day, plan extra travel time.",
    "Does anyone have last year's syllabus breakdown?",
    "Just finished revising, feeling okay about tomorrow.",
]


@dataclass
class CandidateItem:
    event_id: str
    source_feed: str
    candidate_text: str
    intended_category: str  # "clean" | "partial" | "near_exact" — demo/debug only
    generated_at: str


def _paraphrase(text: str) -> str:
    """Crude paraphrase for demo purposes: reorders/truncates a question
    stem to simulate a partial leak rather than a verbatim one. This is
    NOT part of the matching logic — it's only used to construct synthetic
    test content."""
    words = text.split()
    if len(words) <= 6:
        return text
    cut = random.randint(len(words) // 2, len(words) - 2)
    return " ".join(words[:cut]) + " ...(rest reportedly circulating)"


def generate_feed_batch(
    reference_questions: List[str],
    batch_size: int = 10,
    clean_ratio: float = 0.6,
    partial_ratio: float = 0.25,
) -> List[CandidateItem]:
    """
    clean_ratio + partial_ratio should be < 1.0; the remainder is
    near_exact. Ratios are approximate (randomized per item).
    """
    items = []
    now = datetime.now(timezone.utc).isoformat()

    for _ in range(batch_size):
        roll = random.random()
        source_feed = random.choice(SOURCE_FEEDS)

        if roll < clean_ratio or not reference_questions:
            text = random.choice(_CLEAN_FILLER)
            category = "clean"
        elif roll < clean_ratio + partial_ratio:
            ref = random.choice(reference_questions)
            text = _paraphrase(ref)
            category = "partial"
        else:
            ref = random.choice(reference_questions)
            # Near-exact: verbatim or near-verbatim, sometimes with light
            # noise (typo-like insertions) to simulate a screenshot/OCR
            # repost rather than a clean copy-paste.
            text = ref if random.random() < 0.5 else ref + " (leaked ahead of exam!!)"
            category = "near_exact"

        items.append(CandidateItem(
            event_id=str(uuid.uuid4()),
            source_feed=source_feed,
            candidate_text=text,
            intended_category=category,
            generated_at=now,
        ))

    return items
