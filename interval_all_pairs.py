import numpy as np
import itertools
from tqdm import tqdm
import pandas as pd
from random import sample
from typing import Dict, List, Tuple


# Создаем хэш таблицу из файла без NaN значений
def create_task_answer_dict(df: pd.DataFrame) -> Dict[str, List[str]]:
    units_dict: Dict[str, List[str]] = {}
    # task - ключи, answers - значения
    for unit, group in df.groupby('task'):
        answers = group['answer'].dropna().tolist()
        if len(answers) >= 2:
            units_dict[str(unit)] = answers
    return units_dict

#def metric(label1: int, label2: int) -> float:
#   return (sum([g for g in range(min(label1, label2 ), max(label1, label2)+1)]) - (label1 + label2) / 2) ** 2

metric=lambda pair: 0 if pair[0] == pair[1] else 1


def calculate_bootstrapped_alpha(
        units_dict: Dict[str, List[str]],
        D_e: float,
        num_samples: int = 2000,
        metric=lambda pair: 0 if pair[0] == pair[1] else 1,
        p_value: float = 0.05) -> Dict[str, Tuple[float, float]]:
    num_dig: int = len(str(num_samples))
    # Хэш таблица с альфами
    alpha_dict: Dict[int, int] = {}
    # Количество всех пар
    N_0: int = np.sum(
        [len(answers) * (len(answers) - 1) // 2 for unit, answers in units_dict.items()]
    )
    # Количество значений в матрице
    N_dot: int = sum(len(answers) for answers in units_dict.values())

    # Массив всех возможных пар
    pairs: List[Tuple[str, str]] = []
    for unit, answers in units_dict.items():
        unit_pairs = list(itertools.combinations(answers, 2))
        pairs.extend(unit_pairs)

    errors: List[float] = [2 * metric(pair) / (N_dot * D_e) for pair in pairs]

    for _ in tqdm(range(num_samples), ncols=80, desc='Progress'):
        alpha: float = 1.0
        for unit, answers in units_dict.items():
            num_observers: int = len(answers)
            num_pairs: int = num_observers * (num_observers - 1) // 2
            #take random pair
            pair_indices: List[int] = sample(range(N_0), num_pairs)

            for i in range(num_pairs):
                r: int = pair_indices[i]
                alpha -= errors[r] / (num_observers - 1)

        alpha_key: int = int(np.ceil(alpha * (10 ** num_dig)))
        if alpha < -1:
            alpha_key = -10 ** num_dig

        alpha_dict[alpha_key] = alpha_dict.get(alpha_key, 0) + 1

    for key in alpha_dict:
        alpha_dict[key] /= num_samples

    # sorting hashtable with alphas
    sorted_alpha_dict: Dict[int, float] = dict(sorted(alpha_dict.items()))

    # Считаем интервал
    cumulative_sum: float = 0.0
    alpha_smallest: float = 0.0
    for alpha, n_alpha in sorted_alpha_dict.items():
        cumulative_sum += n_alpha
        if cumulative_sum >= p_value / 2:
            alpha_smallest = alpha / (10 ** num_dig)
            break

    cumulative_sum = 0.0
    alpha_largest: float = 0.0
    for alpha, n_alpha in reversed(sorted_alpha_dict.items()):
        cumulative_sum += n_alpha
        if cumulative_sum >= p_value / 2:
            alpha_largest = alpha / (10 ** num_dig)
            break

    return {'confidence_interval': (alpha_smallest, alpha_largest)}


# Пример использования
df: pd.DataFrame = pd.read_csv('crowd_labels.tsv', sep='\t', names=['worker', 'task', 'answer'])

tasks_dict: Dict[str, List[str]] = create_task_answer_dict(df)


#result: Dict[str, Tuple[float, float]] = calculate_bootstrapped_alpha(tasks_dict, 0.6812007463452742)
#result: Dict[str, Tuple[float, float]] = calculate_bootstrapped_alpha(tasks_dict, 0.3720007114298609)
result: Dict[str, Tuple[float, float]] = calculate_bootstrapped_alpha(tasks_dict, 0.485570550804453)
print("confidence interval:", result['confidence_interval'])
# alpha crowd_labels5 = 0.5389072914137769, D_e= 0.6812007463452742
# matrix 0-1 confidence interval: (-0.011, 0.041), alpha=0.012737711181569522
