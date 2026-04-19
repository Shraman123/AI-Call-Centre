import asyncio
import logging
from asterisk.agi import AGI
from main import CallHandler

logging.basicConfig(level=logging.INFO)

class AGIServer:
    def __init__(self, host='localhost', port=4573):
        self.host = host
        self.port = port
        self.call_handler = CallHandler()
    
    async def handle_agi_request(self, reader, writer):
        try:
            agi = AGI()
            await agi.setup(reader, writer)
            await self.call_handler.handle_call(agi)
        except Exception as e:
            logging.error(f"AGI handling error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
    
    async def start_server(self):
        server = await asyncio.start_server(
            self.handle_agi_request, 
            self.host, 
            self.port
        )
        
        logging.info(f"AGI server listening on {self.host}:{self.port}")
        
        async with server:
            await server.serve_forever()

if __name__ == "__main__":
    agi_server = AGIServer()
    asyncio.run(agi_server.start_server())
