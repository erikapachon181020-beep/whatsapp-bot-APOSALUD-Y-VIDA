import asyncio
import httpx

SHEET_ID = "1N3xGYFlSsKrUFV6JtrkeBQ_Acc-9ypXlNc9H74qT7N8"

async def test():
    url = "https://docs.google.com/spreadsheets/d/" + SHEET_ID + "/gviz/tq?tqx=out:csv&sheet=Catalogo"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        print(r.text[:800])

asyncio.run(test())
