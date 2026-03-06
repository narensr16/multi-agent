import sys, os
sys.path.insert(0, 'src')

from dotenv import load_dotenv
load_dotenv()

from graph import build_graph
app = build_graph()

initial_state = {
    'user_query': 'I want to go a 3-day trip from bangalore to singapore budget is 30000',
    'messages':   [],
    'destination': None,
    'days':        None,
    'budget':      None,
    'weather':     None,
    'hotels':      None,
    'transport':   None,
    'estimated_cost': None,
    'final_response': None,
}

final = app.invoke(initial_state)
print('\n=== FINAL RESPONSE ===\n')
import sys
with open('test_output_clean.txt', 'w', encoding='utf-8') as f:
    f.write(final.get('final_response', 'NO RESPONSE'))
print("Wrote output to test_output_clean.txt")
