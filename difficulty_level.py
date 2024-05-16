import re
import jsonlines
import json
from data_loader import MyDatasetUnlabeled

unknown = 0
easy = 0
medium = 0 
hard = 0

path = 'data/unlabeled/code_contests_train_python.jsonl'

def get_specification(description: str) -> str:
        description = MyDatasetUnlabeled.replace_description(description)
        constraints_start_token = '\nconstraints\n'
        input_start_token = '\ninput\n'
        end_token = '\noutput\n'

        constraints_start = description.lower().find(constraints_start_token)
        input_start = description.lower().find(input_start_token)
        end = description.lower().find(end_token)

        constraints_start = (
            len(description) if constraints_start < 0 else constraints_start)
        input_start = len(description) if input_start < 0 else input_start

        start = min(constraints_start, input_start)
        start = 0 if start == len(description) else start
        end = len(description) if end < 0 else end

        specification = description[start:end].strip()
        return specification

def replace_description(description: str) -> str:
        description_replacements = [
            ('\\cdots', '...'),
            ('\\dots', '...'),
            ('\\geq', '>='),
            ('\\ge', '>='),
            ('\\gt', '>'),
            ('\\ldots', '...'),
            ('\\leq', '<='),
            ('\\le', '<='),
            ('\\lt', '<'),
            ('\\neq', '!='),
            ('\\ne', '!='),
            ('\\times', '*'),
            ('\u2013', '--'),
            ('\u2014', '---'),
            ('\u2019', "'"),
            ('\u2026', '...'),
            ('\u2192', "->"),
            ('\u2208', "in"),
            ('\u2211', "sum"),
            ('\u2212', '-'),
            ('\u2260', "!="),
            ('\u2264', '<='),
            ('\u2265', '>='),
            ('\u2266', '<='),
            ('\u2295', "xor"),
            ('\u22c5', '*'),
            ('\u2308', ""),
            ('\u2309', ""),
        ]
        for old, new in description_replacements:
            description = description.replace(old, new)
        return description

with jsonlines.open(path) as f:
    for problem in f:
        target_string = get_specification(problem['description'])
        target_string = replace_description(target_string)
        if re.search(r'(?i)(?=.*first line)(?=.*second line)(?=.*third line)', target_string, re.S|re.M):
            hard += 1
            if hard<=500:
                dictionary = {
                    'name': problem['name'],
                    'description': target_string,
                    'grammar': {'productions': '', 'constraints': ''}
                }
                with open('data/unlabeled/hard.jsonl', 'a') as f:
                   json.dump(dictionary, f)
                   f.write('\n')
        elif re.search(r'(?i)(?=.*first line)(?=.*(?:second line | next [a-z] lines))', target_string, re.S|re.M):
            medium += 1 
            # if medium<=2500:
            #     dictionary = {
            #         'name': problem['name'],
            #         'description': target_string,
            #         'grammar': {'productions': '', 'constraints': ''}
            #     }
            #     with open('data/unlabeled/medium.jsonl', 'a') as f:
            #        json.dump(dictionary, f)
            #        f.write('\n')
        elif re.search(r'(?i)(?=.*(?:input is given from Standard Input|given multiple datasets|input consists of multiple datasets | the first and second lines))', target_string, re.S|re.M):
            medium +=1
            # if medium<=2500:
            #     dictionary = {
            #         'name': problem['name'],
            #         'description': target_string,
            #         'grammar': {'productions': '', 'constraints': ''}
            #     }
            #     with open('data/unlabeled/medium.jsonl', 'a') as f:
            #        json.dump(dictionary, f)
            #        f.write('\n')
        elif re.search(r'(?i)(?=.*(?:either))', target_string, re.S|re.M):
            hard +=1
            if hard<=500:
                dictionary = {
                    'name': problem['name'],
                    'description': target_string,
                    'grammar': {'productions': '', 'constraints': ''}
                }
                with open('data/unlabeled/hard.jsonl', 'a') as f:
                   json.dump(dictionary, f)
                   f.write('\n')
          
        elif re.search(r'(?i)(?=.*(?:first line|the only line | single line | only input line))', target_string, re.S|re.M):
            easy +=1
            # print(problem)
            # ss
            # if easy<=1500:
            #     dictionary = {
            #         'name': problem['name'],
            #         'description': target_string,
            #         'grammar': {'productions': '', 'constraints': ''}
            #     }
            #     with open('data/unlabeled/easy.jsonl', 'a') as f:
            #        json.dump(dictionary, f)
            #        f.write('\n')
            
        else:
            #print(target_string)
            unknown +=1
            #if unknown > 10:
            #    break
           

print("Hard:", hard)
print("Medium:", medium)
print("Easy:", easy)
print("Unknown:", unknown)