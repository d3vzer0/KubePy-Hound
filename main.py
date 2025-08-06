import typer
from sync import sync_app
from dump import dump_app


app = typer.Typer()
app.add_typer(sync_app, name="sync")
app.add_typer(dump_app, name="dump")

if __name__ == "__main__":
    app()
