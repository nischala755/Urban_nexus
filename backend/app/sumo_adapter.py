"""Optional real SUMO/TraCI experiment; imports only when explicitly requested."""

import statistics
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from .generator import generate_state
from .network import EDGES


def find_sumo(name="sumo"):
    import shutil

    located = shutil.which(name)
    if located:
        return located
    try:
        import sumolib

        located = sumolib.checkBinary(name)
        return located if Path(located).is_file() else None
    except (ImportError, RuntimeError):
        return None


def build_network(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    nodes = ET.Element("nodes")
    ET.SubElement(nodes, "node", id="DEPOT", x="240", y="1350", type="priority")
    for z in generate_state().zones:
        ET.SubElement(nodes, "node", id=z.id, x=str(z.x * 30), y=str(z.y * 30), type="priority")
    ET.ElementTree(nodes).write(directory / "ward.nod.xml")
    edges = ET.Element("edges")
    for edge in EDGES:
        for a, b in [(edge["a"], edge["b"]), (edge["b"], edge["a"])]:
            ET.SubElement(
                edges,
                "edge",
                attrib={
                    "id": f"{a}_{b}",
                    "from": a,
                    "to": b,
                    "length": str(edge["km"] * 1000),
                    "speed": "11.11",
                    "numLanes": "1" if edge["capacity_vpm"] < 50 else "2",
                    "priority": "1",
                },
            )
    ET.ElementTree(edges).write(directory / "ward.edg.xml")
    subprocess.run(
        [
            find_sumo("netconvert"),
            "--node-files",
            str(directory / "ward.nod.xml"),
            "--edge-files",
            str(directory / "ward.edg.xml"),
            "--output-file",
            str(directory / "ward.net.xml"),
            "--no-turnarounds",
            "false",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return directory / "ward.net.xml"


def run_sumo_case(directory, net, seed, intervention=False):
    import traci

    start = time.perf_counter()
    directory = Path(directory)
    routes = ET.Element("routes")
    ET.SubElement(
        routes, "vType", id="car", vClass="passenger", accel="2.6", decel="4.5", sigma="0.3", maxSpeed="11.11"
    )
    ET.SubElement(
        routes, "vType", id="collection", vClass="truck", length="8", accel="1", decel="4", maxSpeed="8.33"
    )
    background = ["DEPOT_Z01 Z01_Z04 Z04_Z03 Z03_DEPOT", "DEPOT_Z02 Z02_Z04 Z04_Z01 Z01_DEPOT"]
    for i, edges in enumerate(background):
        ET.SubElement(routes, "route", id=f"route{i}", edges=edges)
    ET.SubElement(routes, "route", id="collection_route", edges="DEPOT_Z02 Z02_Z04 Z04_Z03 Z03_DEPOT")
    for i in range(2):
        ET.SubElement(
            routes,
            "flow",
            id=f"background{i}",
            type="car",
            route=f"route{i}",
            begin="0",
            end="600",
            period="4",
        )
    if intervention:
        truck = ET.SubElement(
            routes, "vehicle", id="W07", type="collection", route="collection_route", depart="60"
        )
        ET.SubElement(truck, "stop", lane="Z02_Z04_0", endPos="2280", duration="480")
    route_path = directory / ("action.rou.xml" if intervention else "baseline.rou.xml")
    trip_path = directory / ("action.trip.xml" if intervention else "baseline.trip.xml")
    ET.ElementTree(routes).write(route_path)
    label = "urbannexus-action" if intervention else "urbannexus-baseline"
    traci.start(
        [
            find_sumo(),
            "-n",
            str(net),
            "-r",
            str(route_path),
            "--seed",
            str(seed),
            "--no-step-log",
            "true",
            "--duration-log.disable",
            "true",
            "--no-warnings",
            "true",
            "--tripinfo-output",
            str(trip_path),
            "--tripinfo-output.write-unfinished",
            "true",
        ],
        label=label,
    )
    connection = traci.getConnection(label)
    queues, speeds = [], []
    version = connection.getVersion()[1]
    elapsed = 0
    try:
        while connection.simulation.getMinExpectedNumber() > 0 and elapsed < 3000:
            connection.simulationStep()
            elapsed += 1
            if elapsed % 10 == 0:
                edge_ids = [e for e in connection.edge.getIDList() if not e.startswith(":")]
                queues.append(sum(connection.edge.getLastStepHaltingNumber(e) for e in edge_ids))
                vehicles = connection.vehicle.getIDList()
                if vehicles:
                    speeds.append(statistics.mean(connection.vehicle.getSpeed(v) * 3.6 for v in vehicles))
    finally:
        connection.close()
    trips = ET.parse(trip_path).getroot().findall("tripinfo")
    background_trips = [t for t in trips if t.attrib["id"].startswith("background")]
    return {
        "producer": "SUMO/TraCI",
        "version": version,
        "seed": seed,
        "source_type": "synthetic",
        "intervention": intervention,
        "simulated_seconds": elapsed,
        "trips": len(trips),
        "unfinished_trips": sum(float(t.attrib["arrival"]) < 0 for t in trips),
        "mean_background_delay_seconds": statistics.mean(
            float(t.attrib["timeLoss"]) for t in background_trips
        ),
        "mean_background_travel_seconds": statistics.mean(
            float(t.attrib["duration"]) for t in background_trips
        ),
        "average_speed_kph": statistics.mean(speeds),
        "max_queue_vehicles": max(queues),
        "runtime_seconds": time.perf_counter() - start,
    }


def run_validation(directory, seed=42):
    if not find_sumo() or not find_sumo("netconvert"):
        return {"status": "unavailable", "fallback": "Python fluid queue", "source_type": "synthetic"}
    directory = Path(directory).resolve()
    net = build_network(directory)
    baseline = run_sumo_case(directory, net, seed, False)
    action = run_sumo_case(directory, net, seed, True)
    return {
        "status": "executed",
        "source_type": "synthetic",
        "seed": seed,
        "baseline": baseline,
        "action": action,
        "background_delay_delta_seconds": action["mean_background_delay_seconds"]
        - baseline["mean_background_delay_seconds"],
        "limitation": "Separate microscopic experiment; not field calibration or a substitute for the fluid-model gate.",
    }
