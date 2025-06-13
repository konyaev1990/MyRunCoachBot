from aiohttp import web
import asyncio
import bot

routes = web.RouteTableDef()

@routes.get('/')
async def home(request):
    return web.Response(text="Bot is running!")

app = web.Application()
app.add_routes(routes)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(bot.main())
    web.run_app(app, port=10000)