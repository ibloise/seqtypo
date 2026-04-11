import io
import logging

from seqtypo import configure_logger, get_logger, models


def test_configure_logger_routes_messages_to_custom_handler():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)

    logger = configure_logger(level=logging.INFO, handler=handler, propagate=False)
    logger.info("hello from seqtypo")

    assert "hello from seqtypo" in stream.getvalue()


def test_scheme_list_get_content_uses_logger(caplog):
    configure_logger(level=logging.INFO, propagate=True)
    caplog.set_level(logging.INFO, logger=get_logger().name)

    scheme_list = models.SchemeList(
        [
            models.SchemeModel(
                scheme="https://example.org/schemes/1",
                description="Simple MLST scheme",
            )
        ]
    )

    content = scheme_list.get_content()

    assert len(content) == 1
    assert "Simple MLST scheme" in caplog.text
