import asyncio

async def indefinite_task():
    try:
        while True:
            print("Indefinite task running... Press Ctrl+C to stop.")
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print("Indefinite task was cancelled.")
    finally:
        print("Cleaning up indefinite task.")

def main():
    loop = asyncio.new_event_loop()  # Create a new event loop
    asyncio.set_event_loop(loop)     # (Optional) Set it as the current event loop

    task = loop.create_task(indefinite_task())  # Create the indefinite task
    try:
        loop.run_forever()  # Run the loop indefinitely
    except KeyboardInterrupt:
        print("\nReceived KeyboardInterrupt! Stopping the loop...")
        task.cancel()  # Cancel the indefinite task
        try:
            loop.run_until_complete(task)  # Wait for the task to finish cleaning up
        except asyncio.CancelledError:
            pass  # If the task was cancelled, we can ignore this
    finally:
        loop.close()  # Close the loop
        print("Event loop closed.")

if __name__ == "__main__":
    main()
