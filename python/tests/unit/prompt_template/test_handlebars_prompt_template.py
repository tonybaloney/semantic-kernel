import pytest
from pytest import mark

from semantic_kernel.connectors.ai.open_ai.contents.function_call import FunctionCall
from semantic_kernel.connectors.ai.open_ai.contents.open_ai_chat_message_content import OpenAIChatMessageContent
from semantic_kernel.connectors.ai.open_ai.contents.tool_calls import ToolCall
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.exceptions import HandlebarsTemplateRenderException, HandlebarsTemplateSyntaxError
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.kernel import Kernel
from semantic_kernel.prompt_template.handlebars_prompt_template import HandlebarsPromptTemplate
from semantic_kernel.prompt_template.prompt_template_config import PromptTemplateConfig


def create_handlebars_prompt_template(template: str) -> HandlebarsPromptTemplate:
    return HandlebarsPromptTemplate(
        prompt_template_config=PromptTemplateConfig(
            name="test", description="test", template=template, template_format="handlebars"
        )
    )


def test_init():
    template = HandlebarsPromptTemplate(
        prompt_template_config=PromptTemplateConfig(
            name="test", description="test", template="{{input}}", template_format="handlebars"
        )
    )
    assert template.prompt_template_config.template == "{{input}}"


def test_init_fail():
    with pytest.raises(HandlebarsTemplateSyntaxError):
        HandlebarsPromptTemplate(
            prompt_template_config=PromptTemplateConfig(
                name="test", description="test", template="{{(input)}}", template_format="handlebars"
            )
        )


def test_init_template_validation_fail():
    with pytest.raises(ValueError):
        HandlebarsPromptTemplate(
            prompt_template_config=PromptTemplateConfig(
                name="test", description="test", template="{{(input)}}", template_format="semantic-kernel"
            )
        )


def test_config_without_prompt():
    config = PromptTemplateConfig(name="test", description="test", template_format="handlebars")
    template = HandlebarsPromptTemplate(prompt_template_config=config)
    assert template._template_compiler is None


@mark.asyncio
async def test_render_without_prompt(kernel: Kernel):
    config = PromptTemplateConfig(name="test", description="test", template_format="handlebars")
    template = HandlebarsPromptTemplate(prompt_template_config=config)
    rendered = await template.render(kernel, None)
    assert rendered == ""


@mark.asyncio
async def test_it_renders_variables(kernel: Kernel):
    template = "Foo {{#if bar}}{{bar}}{{else}}No Bar{{/if}}"
    target = create_handlebars_prompt_template(template)

    rendered = await target.render(kernel, KernelArguments(bar="Bar"))
    assert rendered == "Foo Bar"

    rendered = await target.render(kernel, KernelArguments())
    assert rendered == "Foo No Bar"


@mark.asyncio
async def test_it_renders_nested_variables(kernel: Kernel):
    template = "{{foo.bar}}"
    target = create_handlebars_prompt_template(template)

    rendered = await target.render(kernel, KernelArguments(foo={"bar": "Foo Bar"}))
    assert rendered == "Foo Bar"


@mark.asyncio
async def test_it_renders_with_comments(kernel: Kernel):
    template = "{{! This comment will not show up in the output}}{{bar}}"
    target = create_handlebars_prompt_template(template)

    rendered = await target.render(kernel, KernelArguments(bar="Bar"))
    assert rendered == "Bar"


@mark.asyncio
async def test_it_renders_fail(kernel: Kernel):
    template = "{{ plug-func 'test1'}}"
    target = create_handlebars_prompt_template(template)
    with pytest.raises(HandlebarsTemplateRenderException):
        await target.render(kernel, KernelArguments())


@mark.asyncio
async def test_it_renders_list(kernel: Kernel):
    template = "List: {{#each items}}{{this}}{{/each}}"
    target = create_handlebars_prompt_template(template)

    rendered = await target.render(kernel, KernelArguments(items=["item1", "item2", "item3"]))
    assert rendered == "List: item1item2item3"


@mark.asyncio
async def test_it_renders_kernel_functions_arg_from_template(kernel: Kernel, decorated_native_function):
    kernel.register_function_from_method(plugin_name="plug", method=decorated_native_function)
    template = "Function: {{plug-getLightStatus arg1='test'}}"
    target = create_handlebars_prompt_template(template)

    rendered = await target.render(kernel, KernelArguments())
    assert rendered == "Function: test"


@mark.asyncio
async def test_it_renders_kernel_functions_arg_from_arguments(kernel: Kernel, decorated_native_function):
    kernel.register_function_from_method(plugin_name="plug", method=decorated_native_function)
    template = "Function: {{plug-getLightStatus}}"
    target = create_handlebars_prompt_template(template)

    rendered = await target.render(kernel, KernelArguments(arg1="test"))
    assert rendered == "Function: test"


@mark.parametrize(
    "function, input, expected",
    [
        ("array", "'test1' 'test2' 'test3'", "['test1', 'test2', 'test3']"),
        ("range", "5", "[0, 1, 2, 3, 4]"),
        ("range", "0 5", "[0, 1, 2, 3, 4]"),
        ("range", "0 '5'", "[0, 1, 2, 3, 4]"),
        ("range", "0 5 1", "[0, 1, 2, 3, 4]"),
        ("range", "0 5 2", "[0, 2, 4]"),
        ("range", "0 5 1 1", "[]"),
        ("range", "'a' 5", "[0, 1, 2, 3, 4]"),
        ("concat", "'test1' 'test2' 'test3'", "test1test2test3"),
        ("or", "true false", "true"),
        ("add", "1 2", "3.0"),
        ("add", "1 2 3", "6.0"),
        ("subtract", "1 2 3", "-4.0"),
        ("equals", "1 2", "false"),
        ("equals", "1 1", "true"),
        ("equals", "'test1' 'test2'", "false"),
        ("equals", "'test1' 'test1'", "true"),
        ("less_than", "1 2", "true"),
        ("lessThan", "1 2", "true"),
        ("less_than", "2 1", "false"),
        ("less_than", "1 1", "false"),
        ("greater_than", "2 1", "true"),
        ("greaterThan", "2 1", "true"),
        ("greater_than", "1 2", "false"),
        ("greater_than", "2 2", "false"),
        ("less_than_or_equal", "1 2", "true"),
        ("lessThanOrEqual", "1 2", "true"),
        ("less_than_or_equal", "2 1", "false"),
        ("less_than_or_equal", "1 1", "true"),
        ("greater_than_or_equal", "1 2", "false"),
        ("greaterThanOrEqual", "1 2", "false"),
        ("greater_than_or_equal", "2 1", "true"),
        ("greater_than_or_equal", "1 1", "true"),
        ("camel_case", "'test_string'", "TestString"),
        ("camelCase", "'test_string'", "TestString"),
        ("snake_case", "'TestString'", "test_string"),
        ("snakeCase", "'TestString'", "test_string"),
    ],
)
@mark.asyncio
async def test_helpers(function, input, expected, kernel: Kernel):
    template = f"{{{{ {function} {input} }}}}"
    target = create_handlebars_prompt_template(template)

    rendered = await target.render(kernel, None)
    assert rendered == expected


@mark.asyncio
async def test_helpers_set_get(kernel: Kernel):
    template = """{{set name="arg" value="test"}}{{get 'arg'}} {{arg}}"""
    target = create_handlebars_prompt_template(template)

    rendered = await target.render(kernel, None)
    assert rendered == "test test"


@mark.asyncio
async def test_helpers_set_get_args(kernel: Kernel):
    template = """{{set "arg" "test"}}{{get 'arg'}} {{arg}}"""
    target = create_handlebars_prompt_template(template)

    rendered = await target.render(kernel, None)
    assert rendered == "test test"


@mark.asyncio
async def test_helpers_empty_get(kernel: Kernel):
    template = """{{get}}"""
    target = create_handlebars_prompt_template(template)

    rendered = await target.render(kernel, None)
    assert rendered == ""


@mark.asyncio
async def test_helpers_set_get_from_kernel_arguments(kernel: Kernel):
    template = """{{set name="arg" value=(get 'arg1') }}{{get 'arg'}} {{arg}} {{arg1}}"""
    target = create_handlebars_prompt_template(template)

    rendered = await target.render(kernel, KernelArguments(arg1="test"))
    assert rendered == "test test test"


@mark.asyncio
async def test_helpers_array_from_args(kernel: Kernel):
    template = """{{array arg1 arg2 arg3}}"""
    target = create_handlebars_prompt_template(template)

    rendered = await target.render(kernel, KernelArguments(arg1="test1", arg2="test2", arg3="test3"))
    assert rendered == "['test1', 'test2', 'test3']"


@mark.asyncio
async def test_helpers_double_open_close(kernel: Kernel):
    template = "{{double_open}}{{double_close}}"
    target = create_handlebars_prompt_template(template)

    rendered = await target.render(kernel, None)
    assert rendered == "{{}}"


@mark.asyncio
async def test_helpers_json(kernel: Kernel):
    template = "{{json input_json}}"
    target = create_handlebars_prompt_template(template)

    rendered = await target.render(kernel, KernelArguments(input_json={"key": "value"}))
    assert rendered == '{"key": "value"}'


@mark.asyncio
async def test_helpers_json_empty(kernel: Kernel):
    template = "{{json}}"
    target = create_handlebars_prompt_template(template)

    rendered = await target.render(kernel, None)
    assert rendered == ""


@mark.asyncio
async def test_helpers_message(kernel: Kernel):
    template = """
{{#each chat_history}}
    {{#message role=role}}
    {{~content~}}
    {{/message}}
{{/each}}
"""
    target = create_handlebars_prompt_template(template)
    chat_history = ChatHistory()
    chat_history.add_user_message("User message")
    chat_history.add_assistant_message("Assistant message")
    rendered = await target.render(kernel, KernelArguments(chat_history=chat_history))
    assert (
        rendered.strip()
        == """<message role="user">User message</message><message role="assistant">Assistant message</message>"""
    )


@mark.asyncio
async def test_helpers_openai_message_tool_call(kernel: Kernel):
    template = """{{#each chat_history}}{{#message role=role tool_calls=tool_calls tool_call_id=tool_call_id}}{{~content~}}{{/message}} {{/each}}"""  # noqa E501
    target = create_handlebars_prompt_template(template)
    chat_history = ChatHistory()
    chat_history.add_message(ChatMessageContent(role="user", content="User message"))
    chat_history.add_message(
        OpenAIChatMessageContent(
            role="assistant", tool_calls=[ToolCall(id="test", function=FunctionCall(name="plug-test"))]
        )
    )
    chat_history.add_message(OpenAIChatMessageContent(role="tool", content="Tool message", tool_call_id="test"))
    rendered = await target.render(kernel, KernelArguments(chat_history=chat_history))

    assert (
        rendered.strip()
        == """<message role="user">User message</message> <message role="assistant" tool_calls="[ToolCall(id=\'test\', type=\'function\', function=FunctionCall(name=\'plug-test\', arguments=None))]"></message> <message role="tool" tool_call_id="test">Tool message</message>"""  # noqa E501
    )


@mark.asyncio
async def test_helpers_message_to_prompt(kernel: Kernel):
    template = """{{#each chat_history}}{{message_to_prompt}} {{/each}}"""
    target = create_handlebars_prompt_template(template)
    chat_history = ChatHistory()
    chat_history.add_message(OpenAIChatMessageContent(role="user", content="User message"))
    chat_history.add_message(
        OpenAIChatMessageContent(
            role="assistant", tool_calls=[ToolCall(id="test", function=FunctionCall(name="plug-test"))]
        )
    )
    rendered = await target.render(kernel, KernelArguments(chat_history=chat_history))

    assert (
        rendered.strip()
        == """<message role="user">User message</message> <message role="assistant" tool_calls="{&quot;id&quot;:&quot;test&quot;,&quot;type&quot;:&quot;function&quot;,&quot;function&quot;:{&quot;name&quot;:&quot;plug-test&quot;}}"></message>"""  # noqa E501
    )


@mark.asyncio
async def test_helpers_message_to_prompt_other(kernel: Kernel):
    template = """{{#each other_list}}{{message_to_prompt}} {{/each}}"""
    target = create_handlebars_prompt_template(template)
    other_list = ["test1", "test2"]
    rendered = await target.render(kernel, KernelArguments(other_list=other_list))
    assert rendered.strip() == """test1 test2"""


@mark.asyncio
async def test_helpers_messageToPrompt_other(kernel: Kernel):
    template = """{{#each other_list}}{{messageToPrompt}} {{/each}}"""
    target = create_handlebars_prompt_template(template)
    other_list = ["test1", "test2"]
    rendered = await target.render(kernel, KernelArguments(other_list=other_list))
    assert rendered.strip() == """test1 test2"""
