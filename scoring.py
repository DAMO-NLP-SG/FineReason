from pydantic import BaseModel
from typing import List

from data_loading import Sample

class Scorer(BaseModel):
    def run(self, sample: Sample) -> float:
        raise NotImplementedError


class StateTransitionAccuracyScorer(Scorer):
    def run(self, sample: Sample) -> float:
        if sample.pred == "1":
            return 1.0
        return 0.0


class StateCheckingAccuracyScorer(Scorer):
    def run(self, sample: Sample) -> float:
        if sample.pred == sample.outputs["current_status"]:
            return 1.0
        return 0.0


def select_scorer(scorer_name: str) -> Scorer:
    if scorer_name == "state_transition_accuracy":
        return StateTransitionAccuracyScorer()
    elif scorer_name == "state_checking_accuracy":
        return StateCheckingAccuracyScorer()
    else:
        raise ValueError(f"Scorer {scorer_name} not found")