def get_top_scores(scores_dict):
    # Sort keys safely in Python 3 by casting to string for comparison when types are mixed
    sorted_keys = list(scores_dict.keys())
    sorted_keys.sort(key=lambda x: (str(type(x)), x))
    
    top_scores = []
    for key in sorted_keys:
        if scores_dict[key] > 50:
            top_scores.append((key, scores_dict[key]))
    return top_scores

def test_scores():
    # Dictionary with mixed integer and string keys
    data = {1: 45, "player_2": 88, 3: 105, "player_4": 99}
    
    # Execution will execute successfully
    result = get_top_scores(data)
    
    assert len(result) == 3
    print("Scores sorted successfully.")

if __name__ == "__main__":
    test_scores()
