from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Log, Static
from textual.containers import Horizontal, Vertical

class SARDashboard(App):
    CSS = """
    Screen {
        background: #1a1a1a;
    }
    #title {
        text-align: center;
        background: $accent;
        color: white;
        height: 1;
    }
    #telemetry { 
        height: 3; 
        border: solid green; 
        padding: 0 1;
    }
    #middle-container {
        height: 3fr;
    }
    #model-output { 
        width: 1fr;  
        border: solid cyan; 
    }
    #ros-logs { 
        width: 1fr;  
        border: solid yellow; 
    }
    #alerts { 
        height: 1fr; 
        border: solid red; 
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("SAR DRONE COMMAND", id="title")
        with Vertical():
            yield Static("GPS: --  ALT: --  BAT: --  MODE: --", id="telemetry")
            with Horizontal(id="middle-container"):
                yield Log(id="model-output", highlight=True)
                yield Log(id="ros-logs")
            yield Log(id="alerts")
        yield Footer()

    async def update_telemetry(self, data: dict):
        self.query_one("#telemetry", Static).update(
            f"GPS: {data['lat']:.4f},{data['lon']:.4f}  "
            f"ALT: {data['alt']:.1f}m  "
            f"BAT: {data['battery']}%  "
            f"MODE: {data['mode']}"
        )

    def log_model(self, text: str):
        self.query_one("#model-output", Log).write_line(text)

    def log_ros(self, text: str):
        self.query_one("#ros-logs", Log).write_line(text)

    def log_alert(self, text: str):
        self.query_one("#alerts", Log).write_line(f"🚨 {text}")

if __name__ == "__main__":
    app = SARDashboard()
    app.run()

