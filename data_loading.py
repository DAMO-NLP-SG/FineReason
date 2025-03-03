import json
import random
from pathlib import Path
from typing import List

from fire import Fire
from pydantic import BaseModel

class Sample(BaseModel):
    inputs: dict = {}
    outputs: dict = {}
    prompt: str = ""
    raw_output: str = ""
    pred: str = ""


class Data(BaseModel):
    samples: List[Sample]

    @classmethod
    def load(cls, path: str):
        with open(path, "r") as f:
            samples = [Sample(**json.loads(line)) for line in f]
        return cls(samples=samples)

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            for sample in self.samples:
                print(sample.json(), file=f)

    def analyze(self, seed: int = 0):
        random.seed(seed)
        for sample in random.sample(self.samples, k=10):
            print(json.dumps(sample.json(), indent=2))
        info = dict(
            samples=len(self.samples),
            unique_samples=len(set(s.json() for s in self.samples)),
        )
        print(json.dumps(info, indent=2))


def select_data(name: str, **kwargs):
    if name == "sudoku":
        return Data.load("data/sudoku_questions.json")
    elif name == "sudoku_states":
        return Data.load("data/sudoku_states.json")
    elif name == "graphcoloring":
        return Data.load("data/graphcoloring_questions.json")
    elif name == "graphcoloring_states":
        return Data.load("data/graphcoloring_states.json")
    elif name == "game24":
        return Data.load("data/game24_questions.json")
    elif name == "game24_states":
        return Data.load("data/game24_states.json")
    elif name == "gridpuzzle":
        return Data.load("data/gridpuzzle_questions.json")
    elif name == "gridpuzzle_states":
        return Data.load("data/gridpuzzle_states.json")
    else:
        raise KeyError(name)


def test_data(name: str, **kwargs):
    data = select_data(name, **kwargs)
    data.analyze()


if __name__ == "__main__":
    Fire()