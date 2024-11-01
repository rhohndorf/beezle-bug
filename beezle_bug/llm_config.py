import beezle_bug.template as template

DEFAULT_TEMPLATE = "default_prompt"


class LlmConfig:
    def __init__(
        self,
        msg_start: str,
        msg_stop: str,
        hdr_start: str = "",
        hdr_stop: str = "",
    ) -> None:
        self.msg_start = msg_start
        self.msg_stop = msg_stop
        self.hdr_start = hdr_start
        self.hdr_stop = hdr_stop
        self.template = template.load(DEFAULT_TEMPLATE)


CHATML = LlmConfig("<|im_start|>", "<|im_end|>")
GEMMA = LlmConfig("<start_of_turn>", "<end_of_turn>")
LLAMA = LlmConfig("", "<|eot_id|>", "<|start_header_id|>", "<|stop_header_id|>")
