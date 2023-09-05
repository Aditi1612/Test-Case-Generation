import json
import os
from glob import glob
from pathlib import Path
from collections import OrderedDict
from typing import (Any, )

import torch
import argparse
from transformers import RobertaTokenizer  # type: ignore [import]
from transformers import T5ForConditionalGeneration  # type: ignore [import]

from data_loader import get_data_loader
from tokenizer import CountingContextFreeGrammarTokenizer as CCFGTokenizer
from counting_context_free_grammar import CountingContextFreeGrammar as CCFG


def main(config: dict[str, Any]) -> None:

    save_dir = Path(config['trainer']['save_dir'])
    checkpoint_paths = glob(str(save_dir / '*'))
    latest_checkpoint_path = max(checkpoint_paths, key=os.path.getctime)

    print(f"Checkpoint: {latest_checkpoint_path}")
    checkpoint = torch.load(latest_checkpoint_path)
    state_dict = checkpoint['model_state_dict']

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    model = T5ForConditionalGeneration.from_pretrained(config['pretrained'])
    model.load_state_dict(state_dict)
    model = model.to(device)

    source_tokenizer = RobertaTokenizer.from_pretrained(config['pretrained'])
    target_tokenizer = CCFGTokenizer(source_tokenizer)

    data_dir = Path(config['data_dir'])
    test_data_path = data_dir / config['valid_data']

    data_loader_args = config['data_loader']['args']
    data_loader_args['batch_size'] = 1

    data_loader = get_data_loader(
        test_data_path, source_tokenizer, target_tokenizer,
        **data_loader_args
    )

    generate_args = config['generate']['args']
    with torch.no_grad():
        for batch_idx, batch in enumerate(data_loader):

            sources = batch['sources']
            targets = batch['targets']

            input_ids = sources.input_ids.to(device)
            attention_mask = sources.attention_mask.to(device)
            labels = targets.input_ids.to(device)

            outputs = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                **generate_args
            )

            print(f'Batch {batch_idx}:')
            for y, output in zip(labels.tolist(), outputs.tolist()):

                print("Goal:")
                target_decoding = target_tokenizer.decode(y)
                print(target_decoding)

                print("Output:")
                grammar = target_tokenizer.decode_to_json(output)
                try:
                    CCFG(**grammar)
                    print(grammar)
                except Exception:
                    print("Invalid grammar")


if __name__ == "__main__":
    with open('./config.json') as fp:
        config = json.load(fp, object_hook=OrderedDict)

    parser = argparse.ArgumentParser()
    parser.add_argument('--save-dir', type=Path)
    args = parser.parse_args()
    for k, v in vars(args).items():
        if v is not None:
            config['trainer'][k] = v
    main(config)
