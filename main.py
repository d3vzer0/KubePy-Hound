import typer
from kubepyhound.sync import sync_app, convert_app, shared_commands
from kubepyhound.dump import dump_app


app = typer.Typer()
app.add_typer(sync_app, name="sync")
app.add_typer(dump_app, name="dump")
app.add_typer(convert_app, name="dump")
shared_commands(sync_app)
shared_commands(convert_app)

if __name__ == "__main__":
    app()
