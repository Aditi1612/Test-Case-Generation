import argparse
import json
import logging
import random
from pathlib import Path
from typing import (Any, )

import jsonlines
import torch
import numpy as np
from tqdm import tqdm
# from tqdm.contrib.logging import tqdm_logging_redirect
from data_loader import MyDataset

from validator import get_completeness
from validator import get_soundness


# Fix random seeds for reproducibility
SEED = 42
torch.manual_seed(SEED)  # pytorch random seed
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False
np.random.seed(SEED)  # numpy random seed
random.seed(SEED)  # python random seed


def main(config: dict[str, Any]):

    solution_prefix = Path(config['solution_prefix'])

    # Set variables related to `validate_labeling_config`
    validate_labeling_config = config['validate_labeling']
    logging.info(validate_labeling_config)
    labeled_path = validate_labeling_config['labeled_data']
    testcases_path = validate_labeling_config['testcase']
    output_path = validate_labeling_config['output']
    get_soundness_args = validate_labeling_config['get_soundness']['args']
    get_completeness_args = (
        validate_labeling_config['get_completeness']['args'])

    testcases_dictionary: dict[list[str]] = {}
    with jsonlines.open(testcases_path, 'r') as dataset:
        for data in tqdm(dataset, desc='Loading testcases'):
            name = data['name']
            testcases = data['public_tests']['input']
            # testcases.extend(data['private_tests']['input'])
            # testcases.extend(data['generated_tests']['input'])
            testcases_dictionary[name] = testcases

    soundness = []
    completeness = []

    sound_and_complete_dataset = []
    labeled_dataset = jsonlines.open(labeled_path, 'r')
    for labeled_data in tqdm(labeled_dataset, desc=f'Testing {labeled_path}'):
        grammar = labeled_data['grammar']
        name = labeled_data['name']
        description = labeled_data['description']
        specification = MyDataset.get_specification(description)
        testcases = testcases_dictionary[name]
        solution_dir = solution_prefix / name

        is_sound = get_soundness(
            grammar,
            solution_dir,
            solution_sampling_seed=42,
            name=name,
            specification=specification,
            **get_soundness_args
        )
        is_complete = get_completeness(
            grammar, testcases,
            name=name,
            specification=specification,
            **get_completeness_args
        )
        if is_sound and is_complete:
            sound_and_complete_dataset.append(labeled_data)

        soundness.append(is_sound)
        completeness.append(is_complete)
    correctness = list(map(lambda e: all(e), zip(completeness, soundness)))

    labeled_dataset.close()
    average_soundness = sum(soundness) / len(soundness)
    average_completeness = sum(completeness) / len(completeness)
    average_correctness = sum(correctness) / len(correctness)

    with jsonlines.open(f'data/output_path', 'w') as output:
        
        output.write_all(sound_and_complete_dataset)

    print("Soundness & Completeness & Sound. \\& Compl. \\\\")
    print(f"{average_soundness * 100:.2f} & ", end='')
    print(f"{average_completeness * 100:.2f} & ", end='')
    print(f"{average_correctness * 100:.2f} \\\\")


if __name__ == "__main__":
    logger = logging.getLogger('validator')
    logger.setLevel(logging.ERROR)
    #logger.setLevel(logging.INFO)
    logger.addHandler(logging.FileHandler('validate_labeling.log'))

    parser = argparse.ArgumentParser()
    parser.add_argument('--labeled-data')
    parser.add_argument('--testcase')
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--output', default='/dev/null')
    args = parser.parse_args()

    with open('./config.json') as fp:
        config = json.load(fp)

    data_dir = Path(config['data_dir'])
    unlabeled_test_data = data_dir / config['unlabeled_test_data']
    unlabeled_valid_data = data_dir / config['unlabeled_valid_data']
    testcases_path = (
        unlabeled_test_data if args.test else unlabeled_valid_data)
    trainer_config = config['trainer']
    model_dir = Path(trainer_config['save_dir'])
    labeled_data_base = (
        'model_labeled_test_data.jsonl' if args.test
        else 'model_labeled_valid_data.jsonl'
    )
    labeled_data = model_dir / labeled_data_base

    defaults = {
        'labeled_data': labeled_data,
        'testcase': testcases_path,
        'output': args.output,
    }

    task = 'validate_labeling'
    task_config = config.setdefault(task, {})
    for k in defaults.keys():
        if getattr(args, k, None) is not None:
            task_config[k] = getattr(args, k)
        task_config.setdefault(k, defaults[k])

    main(config)
