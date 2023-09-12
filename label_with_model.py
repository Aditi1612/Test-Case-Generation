import argparse
import json
import logging
import os
from pathlib import Path
from typing import (Any, )

import jsonlines
import torch
from tqdm import tqdm
from transformers import GenerationConfig
from transformers import RobertaTokenizer  # type: ignore [import]
from transformers import T5ForConditionalGeneration  # type: ignore [import]

from data_loader import MyDataset
from model import MyModel
from tokenizer import CountingContextFreeGrammarTokenizer as CcfgTokenizer


def main(config: dict[str, Any]) -> None:

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logging.info(f"Use device: {device}")

    pretrained_model_name = config['pretrained']
    source_encoding_args = config['source_encoding']['args']

    # Set variables related to `label_config`
    label_config = config['label']
    logging.info(label_config)
    model_dir = Path(label_config['model_dir'])
    generation_config = GenerationConfig(**label_config['generation_config'])
    unlabeled_data_path = Path(label_config['unlabeled_data_path'])
    output_path = label_config['output']

    checkpoint_paths = model_dir.glob('*.pth')
    latest_checkpoint_path = max(checkpoint_paths, key=os.path.getctime)

    logging.info(f"Use device: {device}")
    logging.info(f"Dataset: {unlabeled_data_path}")
    logging.info(f"Checkpoint: {latest_checkpoint_path}")

    # Create a data loader
    source_tokenizer = RobertaTokenizer.from_pretrained(pretrained_model_name)
    target_tokenizer = CcfgTokenizer(source_tokenizer)

    # Load the model
    production_model = (
        T5ForConditionalGeneration
        .from_pretrained(pretrained_model_name)
    )
    constraint_model = (
        T5ForConditionalGeneration
        .from_pretrained(pretrained_model_name)
    )
    model = MyModel(
        production_model,
        constraint_model,
        source_tokenizer,
        target_tokenizer
    )
    checkpoint = torch.load(latest_checkpoint_path, map_location=device)
    state_dict = checkpoint['model_state_dict']
    model.load_state_dict(state_dict)
    model = model.to(device)

    def label(unlabeled: dict[str, Any]) -> dict[str, Any]:
        prefix = "summarize: "
        name = unlabeled['name']
        description = unlabeled['description']

        # Tokenize description
        specification = MyDataset.get_specification(description)
        encoding = source_tokenizer.encode(
            prefix + specification, **source_encoding_args)
        input_ids = encoding.to(device)

        # Generate grammar
        generated_productions_list, generated_constraints_list = (
            model.generate(input_ids, generation_config))
        productions = generated_productions_list[0]
        constraints = generated_constraints_list[0]
        grammar = {'productions': productions, 'constraints': constraints}

        labeled_data: dict[str, Any] = {}
        labeled_data['name'] = name
        labeled_data['description'] = description
        labeled_data['grammar'] = grammar

        return labeled_data

    unlabeled_dataset = jsonlines.open(unlabeled_data_path, 'r')
    labeled_dataset = map(label, unlabeled_dataset)
    assert os.path.exists(output_path) is False, "Output file already exists"
    with jsonlines.open(output_path, 'w') as writer:
        writer.write_all(tqdm(labeled_dataset, desc='Labeling'))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument('--model-dir')
    parser.add_argument('--unlabeled-data')
    parser.add_argument('--output')
    args = parser.parse_args()

    with open('./config.json') as fp:
        config = json.load(fp)

    data_dir = Path(config['data_dir'])
    unlabeled_data_path = data_dir / config['unlabeled_test_data']
    trainer_config = config['trainer']
    model_dir = Path(trainer_config['save_dir'])
    if args.model_dir is None:
        output = model_dir / 'labeled.jsonl'
    else:
        output = Path(args.model_dir) / 'labeled.jsonl'

    defaults = {
        'model_dir': model_dir,
        'unlabeled_data_path': unlabeled_data_path,
        'output': output
    }

    task = 'label'
    task_config = config.setdefault(task, {})
    for k in defaults.keys():
        if getattr(args, k, None) is not None:
            task_config[k] = getattr(args, k)
        task_config.setdefault(k, defaults[k])

    main(config)
