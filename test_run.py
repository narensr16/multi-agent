import sys, os
sys.path.insert(0, 'src')

from dotenv import load_dotenv
load_dotenv()

from graph import build_graph
app = build_graph()

initial_state = {
    'user_query': 'I want to visit Kodaikanal for 3 days with 30000 budget',
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
print('\n=== FINAL STATE KEYS ===')
for k, v in final.items():
    if k != 'messages':
        print(f'{k}: {str(v)[:120]}')
print('\n=== FINAL RESPONSE ===')
print(final.get('final_response', 'NO RESPONSE'))
