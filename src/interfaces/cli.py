from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from src.core.assistant import VoiceAssistant
import sys

class CLIInterface:
    def __init__(self):
        self.console = Console()
        self.assistant = VoiceAssistant()

    def run(self):
        """Main CLI loop"""
        self.console.print(Panel.fit(
            "[bold green]🎤 Local AI Voice Assistant[/bold green]\n"
            "[cyan]Features:[/cyan] VAD (auto-stop) • Streaming responses • 100% local\n\n"
            "Commands: 'voice' (VAD+streaming), 'text', 'reset', 'quit'",
            border_style="green"
        ))

        try:
            self.assistant.initialize()
            self.console.print("✅ [green]All systems ready![/green]\n")
        except Exception as e:
            self.console.print(f"[red]Initialization failed: {e}[/red]")
            return

        while True:
            try:
                command = Prompt.ask(
                    "[cyan]Choose mode[/cyan]",
                    choices=["voice", "text", "reset", "quit"],
                    default="voice"
                )

                if command == "quit":
                    break
                elif command == "reset":
                    self.assistant.reset()
                    self.console.print("🔄 [yellow]Conversation reset[/yellow]")
                elif command == "voice":
                    self.handle_voice()
                elif command == "text":
                    self.handle_text()

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupted[/yellow]")
                break

        self.console.print("\n[green]👋 Goodbye![/green]")

    def handle_voice(self):
        """Handle voice input with VAD and streaming"""
        try:
            # Use streaming pipeline for minimum latency
            user_text, response = self.assistant.process_voice_query_streaming(use_vad=True)

            if not user_text:
                self.console.print("[yellow]⚠️  No speech detected, try again[/yellow]")
                return

            # Response already spoken via streaming, just confirm
            self.console.print("\n[dim]───────────────────────────────[/dim]")

        except KeyboardInterrupt:
            self.console.print("\n[yellow]⏸️  Cancelled[/yellow]")
        except Exception as e:
            self.console.print(f"[red]❌ Error: {e}[/red]")
            import traceback
            self.console.print(f"[dim]{traceback.format_exc()}[/dim]")

    def handle_text(self):
        """Handle text input"""
        user_input = Prompt.ask("[bold blue]You[/bold blue]")
        if not user_input:
            return

        speak = Prompt.ask("Speak response?", choices=["y", "n"], default="n")
        try:
            response = self.assistant.process_text_query(
                user_input,
                speak=(speak == "y")
            )
            self.display_exchange(user_input, response)
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def display_exchange(self, user_text: str, response: str):
        """Display conversation exchange"""
        self.console.print(f"\n[bold blue]You:[/bold blue] {user_text}")
        self.console.print(f"[bold green]Assistant:[/bold green] {response}")


def main():
    cli = CLIInterface()
    cli.run()


if __name__ == "__main__":
    main()
