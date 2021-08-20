import click
import apodeixi

@click.command()
def apo_cli():
    '''
    Apodeixi KnowledgeBase command tool
    '''
    click.echo('Hello from Apodeixi! Version=' + apodeixi.__version__)