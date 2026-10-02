"""Browser demo or opt-in football flow; uses real API/worker with no mocked responses."""

import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright, expect
from make_demo_video import make_video
from test_e2e import stop_process

ROOT = Path(__file__).resolve().parents[1]
real = bool(os.environ.get("SCOUTAI_E2E_VIDEO"))
panorama = False
BASE_URL = os.environ.get("SCOUTAI_E2E_URL", "http://127.0.0.1:5173").rstrip("/")
API_URL = os.environ.get("SCOUTAI_E2E_API", "http://127.0.0.1:8000").rstrip("/")
MANAGED_WORKER = os.environ.get("SCOUTAI_E2E_MANAGED_WORKER") == "true"
ARTIFACTS = Path(os.environ.get("SCOUTAI_E2E_ARTIFACTS", str(ROOT / "test-artifacts/e2e" / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}-external")))
ARTIFACTS.mkdir(parents=True, exist_ok=True)
video = (
    Path(os.environ["SCOUTAI_E2E_VIDEO"])
    if real
    else make_video(ARTIFACTS / "demo.avi")
)
if real and os.environ.get("SCOUTAI_DEMO_MODE", "true").lower() != "false":
    raise RuntimeError("Football E2E requires SCOUTAI_DEMO_MODE=false")
if real:
    import cv2

    from_source = cv2.VideoCapture(str(video))
    try:
        width, height, frame_count = [
            int(from_source.get(prop))
            for prop in (
                cv2.CAP_PROP_FRAME_WIDTH,
                cv2.CAP_PROP_FRAME_HEIGHT,
                cv2.CAP_PROP_FRAME_COUNT,
            )
        ]
    finally:
        from_source.release()
    panorama = width >= 1920 and width / height >= 3
suffix = secrets.token_hex(4)
player, scout = f"player_{suffix}", f"scout_{suffix}"
password = secrets.token_urlsafe(18)
failures, console_errors, api_responses, steps = [], [], [], []
worker = None
happy_path_errors = None
fixture_name = "Synthetic Demo Player" if not real else "CV Test Player"


def check_layout(page, name):
    for width, height in [(1440, 1000), (768, 1024), (390, 844)]:
        page.set_viewport_size({"width": width, "height": height})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
            f"Overflow: {name} {width}"
        )
        page.screenshot(path=str(ARTIFACTS / f"{name}-{width}.png"), full_page=True)
    page.set_viewport_size({"width": 1440, "height": 1000})


def register(page, username, role):
    page.goto(f"{BASE_URL}/register")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Username", exact=True).fill(username)
    page.get_by_label("Password", exact=True).fill(password)
    page.get_by_label("Account type").select_option(role)
    page.get_by_role("button", name="Create account", exact=True).click()
    expect(page).to_have_url(f"{BASE_URL}/login")
    steps.append(f"register {role}")


def login(page, username):
    page.get_by_label("Username", exact=True).fill(username)
    page.get_by_label("Password", exact=True).fill(password)
    page.get_by_role("button", name="Log in", exact=True).click()
    expect(page.get_by_role("button", name="Log out")).to_be_visible()
    steps.append("login")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1440, "height": 1000}, locale="en-US"
    )
    page = context.new_page()
    page.on("pageerror", lambda error: console_errors.append(str(error)))
    page.on(
        "console",
        lambda message: (
            console_errors.append(message.text) if message.type == "error" else None
        ),
    )
    page.on(
        "response",
        lambda response: (
            api_responses.append({"url": response.url, "status": response.status})
            if response.request.resource_type in ("xhr", "fetch")
            else None
        ),
    )
    try:
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        # Reconnaissance precedes actions; retain rendered DOM and accessible control labels.
        (ARTIFACTS / "initial-dom.html").write_text(page.content(), encoding="utf-8")
        print(
            "Rendered controls:", page.locator("button, label, a").all_text_contents()
        )
        check_layout(page, "login")
        register(page, player, "player")
        login(page, player)
        owner_token = page.evaluate("sessionStorage.getItem('scout_token')")
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        owner_id = context.request.get(f"{API_URL}/profile/me", headers=owner_headers).json()["user"]["id"]
        expect(page.get_by_text("Private profile", exact=True)).to_be_visible()
        page.get_by_role("link", name="Edit profile").click()
        page.get_by_label("Full name").fill(fixture_name)
        page.get_by_label("Position", exact=True).select_option("Forward")
        page.get_by_label("Age", exact=True).fill("22")
        page.get_by_label("Team", exact=True).fill("Synthetic Demo FC" if not real else "Validation fixture")
        page.get_by_label("About you").fill(
            "Left-footed forward. Browser-tested profile."
        )
        page.get_by_role("button", name="Save profile").click()
        expect(page.get_by_role("heading", name=fixture_name)).to_be_visible()
        page.reload()
        expect(page.get_by_role("heading", name=fixture_name)).to_be_visible()
        check_layout(page, "profile")
        steps.extend(["profile edit/save", "profile refresh/auth restore"])
        page.get_by_role("link", name="Analyze a video", exact=True).first.click()
        if real:
            page.get_by_label("Match video").set_input_files(str(video))
        else:
            page.get_by_role("button", name="Use synthetic demo sample").click()
            expect(page.get_by_text("synthetic-demo.avi", exact=True)).to_be_visible()
        check_layout(page, "upload")
        with page.expect_response(
            lambda response: (
                response.url.endswith("/analyses") and response.request.method == "POST"
            )
        ) as uploaded:
            page.get_by_role("button", name="Upload and find players").click()
        assert uploaded.value.status == 202, uploaded.value.text()
        if not MANAGED_WORKER:
            expect(page.get_by_text("Queued for processing", exact=True)).to_be_visible()
        analysis_id = uploaded.value.json()["id"]
        steps.append("upload + queued status")
        # Start the actual durable worker after observing queued, with no mocked API.
        if not MANAGED_WORKER:
            log = (ARTIFACTS / "worker.log").open("w", encoding="utf-8")
            worker = subprocess.Popen(
                [sys.executable, "-m", "app.worker"], cwd=ROOT / "backend",
                env=os.environ.copy(), stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        expect(page.get_by_role("heading", name="Which player are you?")).to_be_visible(
            timeout=120000 if real else 30000
        )
        expect(page.get_by_text("processing", exact=True)).to_be_visible()
        page.reload()
        expect(
            page.get_by_role("heading", name="Which player are you?")
        ).to_be_visible()
        selected_id = 1
        check_layout(page, "gallery")
        if real:
            token = page.evaluate("sessionStorage.getItem('scout_token')")
            analysis_id = page.url.rsplit("/", 1)[-1]
            gallery_response = context.request.get(
                f"{API_URL}/analyses/{analysis_id}/players",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert gallery_response.ok
            gallery = gallery_response.json()["players"]
            selected_id = max(gallery, key=lambda entry: entry["observations"])["id"]
            page.get_by_role("button").filter(
                has=page.get_by_text(f"Player {selected_id}", exact=True)
            ).click()
            # Deliberately invalid physical assumption to test the server-side camera veto.
            # This whole-image rectangle is a UI/geometry fixture, not field ground truth.
            page.get_by_text(
                "Field calibration for distance and speed", exact=True
            ).click()
            page.get_by_label("Enable manual calibration").check()
            if not panorama:
                page.get_by_label(
                    "I confirm the camera stayed fixed throughout this clip"
                ).check()
            coordinates = page.get_by_label(
                "Corner coordinates (JSON; keyboard alternative)"
            )
            coordinates.fill(
                json.dumps(
                    [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]]
                )
            )
            coordinates.blur()
            if panorama:
                # UI correctly refuses physical calibration without fixed-camera confirmation.
                # Continue with the supported image-space report instead of inventing field geometry.
                expect(
                    page.get_by_role("button", name="Build my report")
                ).to_be_disabled()
                page.get_by_label("Enable manual calibration").uncheck()
        else:
            page.get_by_role("button", name="Demo player 1").click()
        page.get_by_role("button", name="Build my report").click()
        expect(page.get_by_role("heading", name="Your match report")).to_be_visible(
            timeout=30000
        )
        expect(page.get_by_text("completed", exact=True)).to_be_visible()
        if real:
            result_response = context.request.get(
                f"{API_URL}/analyses/{analysis_id}/result",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert result_response.ok
            result = result_response.json()
            assert result["demo"] is False and result["device"] in ("cpu", "cuda")
            assert result["frames_processed"] == frame_count
            if panorama:
                assert result["detector_profile"] == "panoramic_person"
                assert result["ground_position_method"] == "bbox_bottom_center"
                assert any("precise foot" in warning for warning in result["warnings"])
            else:
                assert result["camera_motion"]["status"] == "moving"
            assert result["calibration_provided"] == (not panorama)
            assert not result["calibrated"]
            assert all(value is None for value in result["metrics"].values())
            assert result["movement_segments"] and result["annotated_preview"]
            assert result["tracking_quality"]["observed_frame_coverage"] > 0
            (ARTIFACTS / "report.json").write_text(
                json.dumps(result, indent=2), encoding="utf-8"
            )
            if not panorama:
                expect(page.get_by_text("Motion detected", exact=True)).to_be_visible()
            else:
                expect(
                    page.get_by_text("Positions use the bottom", exact=False)
                ).to_be_visible()
            steps.append(
                "real YOLO football, calibration safety gate, unavailable physical metrics"
            )
        else:
            expect(page.get_by_text("1,250.5", exact=False)).to_be_visible()
        page.get_by_role("button", name="Path", exact=True).click()
        expect(
            page.get_by_role("img", name=f"path for player {selected_id}")
        ).to_be_visible()
        page.get_by_role("button", name="Heatmap", exact=True).click()
        if real:
            page.get_by_text("View detected players", exact=True).click()
        assert page.locator("img").evaluate_all(
            "images => images.every(i => i.complete && i.naturalWidth > 0)"
        )
        assert worker is None or worker.poll() is None
        check_layout(page, "report")
        with page.expect_download() as download:
            page.get_by_role("button", name="Export JSON", exact=True).click()
        export_path = ARTIFACTS / "export.json"
        download.value.save_as(export_path)
        exported = json.loads(export_path.read_text())
        assert exported["analysis"]["id"] == analysis_id
        assert exported["report"]["demo"] is (not real)
        assert exported["report"]["warnings"]
        if real:
            assert all(value is None for value in exported["report"]["metrics"].values())
        page.evaluate("() => { window.__printCalls = 0; window.print = () => { window.__printCalls += 1 }; }")
        page.get_by_role("button", name="Print / save PDF").click()
        page.wait_for_function("window.__printCalls === 1")
        page.emulate_media(media="print")
        expect(page.locator('.sidebar')).not_to_be_visible()
        expect(page.locator('.print-title')).to_be_visible()
        page.screenshot(path=str(ARTIFACTS / 'report-print.png'), full_page=True)
        page.pdf(path=str(ARTIFACTS / 'report-print.pdf'), format='A4', print_background=True)
        page.emulate_media(media="screen")
        steps.extend(["protected JSON export", "print action + print CSS/PDF render"])
        page.reload()
        expect(page.get_by_role("heading", name="Your match report")).to_be_visible()
        steps.extend(
            [
                "persisted processing/selection after refresh",
                "player selection",
                "completed report + metrics + heatmap/path",
                "report refresh",
            ]
        )
        page.get_by_role("link", name="My profile", exact=True).click()
        expect(page.get_by_role("heading", name="Match analyses", exact=True)).to_be_visible()
        expect(page.locator('.analysis-list a')).to_have_count(1)
        page.reload()
        expect(page.locator('.analysis-list a')).to_have_count(1)
        steps.append("saved history after refresh")
        page.get_by_role("link", name="Edit profile").click()
        page.get_by_label("Share my profile and completed reports with registered scouts").check()
        page.get_by_role("button", name="Save profile").click()
        expect(page.get_by_text("Shared with scouts", exact=True)).to_be_visible()
        steps.append("explicit publication through profile UI")
        page.get_by_role("button", name="Log out").click()
        register(page, scout, "scout")
        login(page, scout)
        expect(page.get_by_role("heading", name="The scouting room")).to_be_visible()
        page.get_by_label("Search players").fill(player)
        page.get_by_role("button", name="Search", exact=True).click()
        expect(page.get_by_role("heading", name=fixture_name)).to_be_visible()
        check_layout(page, "dashboard")
        page.get_by_role("link", name="View player", exact=True).click()
        expect(page.get_by_role("heading", name="Player detail")).to_be_visible()
        if real:
            if not panorama:
                expect(page.get_by_text("Motion detected", exact=True)).to_be_visible()
            else:
                expect(
                    page.get_by_text("Positions use the bottom", exact=False)
                ).to_be_visible()
        else:
            expect(page.get_by_text("1,250.5", exact=False)).to_be_visible()
        check_layout(page, "player-detail")
        with page.expect_download() as scout_download:
            page.get_by_role("button", name="Export JSON", exact=True).click()
        scout_download.value.save_as(ARTIFACTS / "scout-export.json")
        steps.extend(
            [
                "scout dashboard from API",
                "search created player",
                "player detail + saved report",
            ]
        )
        page.goto(f"{BASE_URL}/upload")
        expect(page.get_by_role("heading", name="The scouting room")).to_be_visible()
        page.goto(f"{BASE_URL}/unknown-page")
        expect(page.get_by_role("heading", name="Page not found")).to_be_visible()
        steps.extend(["scout route guard", "404 fallback"])
        page.goto(f"{BASE_URL}/players/{owner_id}")
        expect(page.get_by_role("button", name="Export JSON", exact=True)).to_be_visible()
        assert not console_errors, console_errors
        assert not [
            response for response in api_responses if response["status"] >= 400
        ], api_responses
        happy_path_errors = {"console": [], "http": []}
        # A second normal login lets the owner revoke sharing through the UI.
        owner_context = browser.new_context(viewport={"width": 1440, "height": 1000})
        owner_page = owner_context.new_page()
        owner_page.goto(f"{BASE_URL}/login")
        login(owner_page, player)
        expect(owner_page.locator('.analysis-list a')).to_have_count(1)
        owner_page.get_by_role("link", name="Edit profile").click()
        owner_page.get_by_label("Share my profile and completed reports with registered scouts").uncheck()
        owner_page.get_by_role("button", name="Save profile").click()
        expect(owner_page.get_by_text("Private profile", exact=True)).to_be_visible()
        scout_token = page.evaluate("sessionStorage.getItem('scout_token')")
        scout_headers = {"Authorization": f"Bearer {scout_token}"}
        assert context.request.get(f"{API_URL}/analyses/{analysis_id}/export", headers=scout_headers).status == 404
        # Keep the previously allowed report open: polling must evict cached private data.
        expect(page.get_by_role("alert")).to_contain_text("no longer shared", timeout=15000)
        expect(page.get_by_role("button", name="Export JSON", exact=True)).to_have_count(0)
        owner_context.close()
        steps.append("owner relogin/history + UI revocation blocks scout detail/export (expected404)")
        # Invalid token is an intentional negative check, separate from the zero-error happy path.
        page.evaluate("sessionStorage.setItem('scout_token', 'invalid')")
        page.goto(f"{BASE_URL}/dashboard")
        expect(page.get_by_role("button", name="Log in", exact=True)).to_be_visible()
        steps.append("invalid JWT clears session and returns to login (expected 401)")
        print("E2E PASS:", "; ".join(steps))
    except Exception as error:
        failures.append(str(error))
        page.screenshot(path=str(ARTIFACTS / "failure.png"), full_page=True)
        raise
    finally:
        (ARTIFACTS / "results.json").write_text(
            json.dumps(
                {
                    "steps": steps,
                    "failures": failures,
                    "console_errors": console_errors,
                    "api_responses": api_responses,
                    "happy_path_errors": happy_path_errors,
                    "negative_checks": "After happy path: revoked sharing expects404, invalid JWT expects401",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        if worker:
            stop_process(worker)
            log.close()
        context.close()
        browser.close()
