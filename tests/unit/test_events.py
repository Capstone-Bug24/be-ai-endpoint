from __future__ import annotations



from capruntime.events import build_analysis_result, build_event





def test_build_event_uses_final_sensor_object_map() -> None:

    event = build_event(

        site_id="S001",

        camera_id="cam01",

        detection={"bbox": {}, "confidence": 0.75, "reason_code": "PROXIMITY_RISK"},

        sensor_snapshot={

            "ultra_front": {

                "sensor": "ultra_front",

                "id": "ultra_front_01",

                "type": "ultrasonic",

                "ts": "2026-05-06T00:00:00Z",

                "zone_ids": ["danger_q2", "forklift_lane"],

                "unit": "m",

                "data": {"distance_m": 1.2, "status": "ok"},

            },

            "ultra_rear": {"data": {"value": 2.4}},

            "note_only": {"data": {"status": "warn"}},

        },

        frame_id=42,

        frame_ts="2026-05-06T00:00:01Z",

    )



    assert event["frame_id"] == 42

    assert event["frame_ts"] == "2026-05-06T00:00:01Z"

    assert event["event_status"] == "ACTIVE"

    assert event["reason"] == {"code": "PROXIMITY_RISK", "factors": []}

    assert "sensor_status" not in event

    assert event["sensors"]["ultra_front"] == {

        "id": "ultra_front_01",

        "type": "ultrasonic",

        "ts": "2026-05-06T00:00:00Z",

        "status": "OK",

        "unit": "m",

        "value": 1.2,

        "zone_ids": ["danger_q2", "forklift_lane"],

    }

    assert event["sensors"]["ultra_rear"]["value"] == 2.4

    assert event["sensors"]["note_only"]["status"] == "WARN"

    assert event["sensors"]["note_only"]["value"] is None





def test_build_event_keeps_sensor_status_inside_each_sensor() -> None:

    event = build_event(

        site_id="S001",

        camera_id="cam01",

        detection={"bbox": {}, "confidence": 0.75},

        sensor_snapshot={

            "ultra_front": {

                "sensor": "ultra_front",

                "ts": "2026-05-06T00:00:00Z",

                "data": {"distance_m": 0.8, "status": "warn"},

            }

        },

    )



    assert "sensor_status" not in event

    assert event["sensors"]["ultra_front"]["status"] == "WARN"

    assert event["sensors"]["ultra_front"]["value"] == 0.8





def test_build_event_applies_rule_sensor_status_override() -> None:

    event = build_event(

        site_id="S001",

        camera_id="cam01",

        detection={

            "bbox": {},

            "confidence": 0.75,

            "sensor_status_overrides": {"ultra_front": "ALERT"},

        },

        sensor_snapshot={"ultra_front": {"data": {"value": 1.5}}},

    )



    assert event["sensors"]["ultra_front"]["status"] == "ALERT"





def test_build_analysis_result_groups_frame_detections_and_alerts() -> None:

    payload = build_analysis_result(

        site_id="S001",

        camera_id="cam01",

        frame_id=7,

        frame_ts="2026-05-06T00:00:01Z",

        frame_shape=(1080, 1920, 3),

        detections=[

            {

                "object_type": "PERSON",

                "event_type": "ZONE_INTRUSION",

                "severity": "HIGH",

                "confidence": 0.91,

                "bbox": {"x1": 10, "y1": 20, "x2": 30, "y2": 40},

                "zones": [

                    {"zone_id": "danger_q2", "inside": True, "zone_type": "quadrant"},

                    {"zone_id": "forklift_lane", "inside": True, "zone_type": "polygon"},

                ],

                "reason_factors": ["PERSON_DETECTED", "ZONE_INTRUSION"],

                "sensor_status_overrides": {"ultra_front": "ALERT"},

            },

            {

                "object_type": "PERSON",

                "event_type": "ZONE_INTRUSION",

                "severity": "HIGH",

                "confidence": 0.88,

                "bbox": {"x1": 100, "y1": 120, "x2": 130, "y2": 160},

                "zone": {"zone_id": "danger_q2", "inside": True},

                "reason_factors": ["PERSON_DETECTED", "ZONE_INTRUSION"],

            },

        ],

        sensor_snapshot={
            "ultra_front": {
                "id": "ultra_front_01",
                "zone_ids": ["danger_q2", "forklift_lane"],
                "data": {"value": 1.5},
            }
        },
        zone_definitions=[
            {
                "zone_id": "danger_q2",
                "zone_type": "quadrant",
                "severity": "HIGH",
                "points_norm": [],
            },
            {
                "zone_id": "forklift_lane",
                "zone_type": "polygon",
                "severity": "HIGH",
                "points_norm": [],
            },
        ],

    )



    assert payload["analysis_id"]

    assert payload["frame_id"] == 7

    assert payload["frame_width"] == 1920

    assert len(payload["detections"]) == 2

    assert payload["zones"] == [
        {
            "zone_id": "danger_q2",
            "zone_type": "quadrant",
            "severity": "HIGH",
            "points_norm": [],
        },
        {
            "zone_id": "forklift_lane",
            "zone_type": "polygon",
            "severity": "HIGH",
            "points_norm": [],
        },
    ]

    assert "zones" not in payload["detections"][0]

    assert "zone" not in payload["detections"][0]

    assert payload["zone_matches"] == [
        {
            "detection_id": payload["detections"][0]["detection_id"],
            "zone_id": "danger_q2",
            "inside": True,
            "basis": "bbox_center",
        },
        {
            "detection_id": payload["detections"][0]["detection_id"],
            "zone_id": "forklift_lane",
            "inside": True,
            "basis": "bbox_center",
        },
        {
            "detection_id": payload["detections"][1]["detection_id"],
            "zone_id": "danger_q2",
            "inside": True,
            "basis": "bbox_center",
        },
    ]

    assert payload["detections"][0]["bbox_norm"] == {
        "x1": 0.005208,
        "y1": 0.018519,
        "x2": 0.015625,
        "y2": 0.037037,
    }

    assert len(payload["alerts"]) == 1

    assert len(payload["alerts"][0]["object_refs"]) == 2

    assert payload["alerts"][0]["zone_refs"] == ["danger_q2", "forklift_lane"]

    assert payload["alerts"][0]["message"] == "작업자 2명 danger_q2, forklift_lane 진입 감지"

    assert payload["sensors"]["ultra_front"]["status"] == "ALERT"

    assert payload["sensors"]["ultra_front"]["zone_ids"] == ["danger_q2", "forklift_lane"]
