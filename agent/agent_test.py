from assistant_cls import Agent
from icecream import ic

agent = Agent()
m1 = "Was ist das für ein Produkt?"
m2 = "Wie viel Fett hat das Produkt?"
m3 = "Wie viele habt ihr auf Lager?"
m4 = "Habt ihr andere Kekese?"

ms = [m1, m2, m3, m4]
thread_id = None
for m in ms:

    content = {
        "msg": m,
        "images": [],
        "barcode": "4016249010201" if m == m1 else None,
    }
    user = {
        "user_id": None,
        "thread_id": thread_id,
    }
    # Test chat method
    ic(m)
    answer, thread_id = agent.chat(content, user)
    ic(answer, thread_id)