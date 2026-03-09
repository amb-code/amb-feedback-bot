import pytest

from feedbackbot.topics.utils import sanitize_topic_name, TOPIC_NAME_MAX_LENGTH


class TestSanitizeTopicName:

    @pytest.mark.parametrize(
        'full_name,username,expected',
        (
            ('John Doe', 'johndoe', 'John Doe (johndoe)'),
            ('John Doe', None, 'John Doe'),
            (None, 'johndoe', 'Без имени (johndoe)'),
        ),
    )
    def test_basic_combinations(self, full_name, username, expected):
        # when
        actual = sanitize_topic_name(full_name, username)

        # then
        assert actual == expected

    def test_trim_and_normalize_whitespace(self):
        # given
        full_name = '  John   \t Doe  '
        username = '  john\tdoe  '
        expected = 'John Doe (john doe)'

        # when
        actual = sanitize_topic_name(full_name, username)

        # then
        assert actual == expected

    def test_remove_control_characters(self):
        # given
        full_name = 'John\x00\x07 Doe'
        username = 'john\x0bdoe'
        expected = 'John Doe (johndoe)'

        # when
        actual = sanitize_topic_name(full_name, username)

        # then
        assert actual == expected

    def test_truncate_to_max_length(self):
        # given
        full_name = 'A' * (TOPIC_NAME_MAX_LENGTH + 10)

        # when
        actual = sanitize_topic_name(full_name, None)

        # then
        assert len(actual) == TOPIC_NAME_MAX_LENGTH

    def test_fallback_to_default_name_when_empty_after_cleaning(self):
        # given
        full_name = '\x00\x07\x08'

        # when
        actual = sanitize_topic_name(full_name, None)

        # then
        assert actual == 'Без имени'

