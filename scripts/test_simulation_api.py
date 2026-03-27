"""Manual test script for simulation API endpoints.

This script tests the simulation bootstrap workflow end-to-end.
Requires a running server with Neo4j and OpenAI API access.

Usage:
    python scripts/test_simulation_api.py
"""

import asyncio
import json
from typing import Any


async def test_simulation_bootstrap():
    """Test the simulation bootstrap endpoint."""
    import httpx

    base_url = "http://localhost:8000"
    timeout = 120.0  # Bootstrap can take time

    async with httpx.AsyncClient(timeout=timeout) as client:
        # Test 1: Bootstrap a new simulation
        print("=" * 60)
        print("Test 1: Bootstrap Simulation")
        print("=" * 60)

        bootstrap_payload = {
            "name": "Test Social Simulation",
            "description": "A test simulation for social dynamics",
            "seed_sources": [
                {
                    "source_type": "TEXT",
                    "content": """
                    In a tech company in Beijing, there's a team of software engineers.
                    The team lead is Zhang Wei, a seasoned engineer with 10 years of experience.
                    Li Na is a front-end specialist who recently joined from a startup.
                    Wang Qiang is the backend expert who has been with the company since founding.
                    They are working on a new AI-powered feature for their product.
                    The team often collaborates with the design team led by Chen Xi.
                    """,
                }
            ],
            "agent_count": 5,
            "platforms": ["WECHAT"],
            "parameters": {
                "max_agents": 10,
                "memory_decay_rate": 0.1,
                "interaction_probability": 0.3,
                "platform_sync_interval": 60,
                "simulation_speed": 1.0,
                "enable_emotion": True,
                "enable_memory_formation": True,
                "enable_relationship_evolution": True,
            },
        }

        try:
            response = await client.post(
                f"{base_url}/api/v1/simulation/bootstrap",
                json=bootstrap_payload,
            )
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"✓ Bootstrap successful!")
                print(f"  Session: {result['session']['name']}")
                print(f"  Agents created: {result['agents_created']}")
                print(f"  Worlds created: {result['worlds_created']}")
                print(f"  Seeds processed: {result['seeds_processed']}")
                print(f"  Status: {result['status']}")
                print(f"  Message: {result['message']}")
            else:
                print(f"✗ Bootstrap failed: {response.text}")

        except httpx.ConnectError as e:
            print(f"✗ Could not connect to server: {e}")
            print("  Make sure the server is running: uvicorn app.main:app --reload")
            return
        except Exception as e:
            print(f"✗ Error: {e}")

        # Test 2: Extract a seed
        print("\n" + "=" * 60)
        print("Test 2: Extract Reality Seed")
        print("=" * 60)

        seed_payload = {
            "source_type": "TEXT",
            "raw_content": """
            The annual tech conference featured keynote speeches from industry leaders.
            Dr. Sarah Chen from MIT presented breakthrough research in quantum computing.
            Multiple startups showcased their AI solutions, including innovations in healthcare and finance.
            The conference fostered networking and collaboration opportunities.
            """,
            "metadata": {"title": "Tech Conference 2024"},
        }

        try:
            response = await client.post(
                f"{base_url}/api/v1/simulation/seeds/extract",
                json=seed_payload,
            )
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"✓ Seed extraction successful!")
                print(f"  Seed ID: {result['seed_id']}")
                print(f"  Entity count: {result['extracted_entity_count']}")
                print(f"  Potential agent count: {result['extracted_agent_count']}")
            else:
                print(f"✗ Seed extraction failed: {response.text}")

        except Exception as e:
            print(f"✗ Error: {e}")

        # Test 3: Generate agents
        print("\n" + "=" * 60)
        print("Test 3: Generate Agent Profiles")
        print("=" * 60)

        agents_payload = {
            "profile_count": 3,
            "platform": "WECHAT",
        }

        try:
            response = await client.post(
                f"{base_url}/api/v1/simulation/agents/generate",
                json=agents_payload,
            )
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"✓ Agent generation successful!")
                print(f"  Agents generated: {len(result['agents'])}")
                for agent in result['agents']:
                    print(f"    - {agent['name']}: {agent['profile']['occupation']}")
            else:
                print(f"✗ Agent generation failed: {response.text}")

        except Exception as e:
            print(f"✗ Error: {e}")

        # Test 4: Configure world
        print("\n" + "=" * 60)
        print("Test 4: Configure Simulation World")
        print("=" * 60)

        world_payload = {
            "world_key": "test_wechat_world",
            "name": "Test WeChat World",
            "description": "A simulated WeChat ecosystem",
            "platform": "WECHAT",
            "state_data": {"initial_population": 100},
        }

        try:
            response = await client.post(
                f"{base_url}/api/v1/simulation/world/configure",
                json=world_payload,
            )
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"✓ World configuration successful!")
                print(f"  World ID: {result['world_id']}")
                print(f"  World Key: {result['world_key']}")
                print(f"  Platform: {result['platform']}")
            else:
                print(f"✗ World configuration failed: {response.text}")

        except Exception as e:
            print(f"✗ Error: {e}")


def main():
    """Run all tests."""
    print("Social Simulation API Tests")
    print("=" * 60)
    print("This script tests the simulation API endpoints.")
    print("Make sure the server is running: uvicorn app.main:app --reload")
    print("=" * 60 + "\n")

    asyncio.run(test_simulation_bootstrap())

    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
