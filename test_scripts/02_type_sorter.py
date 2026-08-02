def get_top_scores(scores_dict):
    # This sort will fail in Python 3 if keys are mixed types
    sorted_keys = list(scores_dict.keys())
    sorted_keys.sort()
    
    top_scores = []
    for key in sorted_keys:
        if scores_dict[key] > 50:
            top_scores.append((key, scores_dict[key]))
    return top_scores

def test_scores():
    # Dictionary with mixed integer and string keys
    data = {1: 45, "player_2": 88, 3: 105, "player_4": 99}
    
    # Execution will crash here
    result = get_top_scores(data)
    
    assert len(result) == 3
    print("Scores sorted successfully.")

if __name__ == "__main__":
    test_scores()