import asyncio
import re

from pydantic import BaseModel

from elan import Node, Workflow, task


class ArticleDraft(BaseModel):
    title: str
    slug: str
    author: str


@task
def prepare_article(title: str, author: str) -> ArticleDraft:
    normalized_title = title.strip()
    normalized_author = author.strip()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized_title.lower()).strip("-")
    return ArticleDraft(
        title=normalized_title,
        slug=slug,
        author=normalized_author,
    )


@task
async def publish_article(slug: str):
    return f"/articles/{slug}"


@task
def build_notification(url: str):
    return f"Article ready at {url}"


workflow = Workflow(
    "publish_article",
    start=Node(run=prepare_article, next="publish"),
    publish=Node(run=publish_article, next="notify"),
    notify=build_notification,
)


if __name__ == "__main__":
    run = asyncio.run(
        workflow.run(
            title="  Launching Elan 0.1  ",
            author=" Hugo ",
        )
    )
    print("Result:", run.result)
