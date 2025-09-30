import typer
from kubepyhound.sync import sync_app, convert_app
from kubepyhound.dump import dump_app

# from kubepyhound.postproc import postproc_app


app = typer.Typer(pretty_exceptions_enable=False)
app.add_typer(dump_app, name="dump")
app.add_typer(convert_app, name="convert")
app.add_typer(sync_app, name="sync")
# app.add_typer(postproc_app, name="postproc")

# shared_commands(sync_app)
# shared_commands(convert_app)

if __name__ == "__main__":
    app()
