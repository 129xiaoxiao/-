from __future__ import annotations

from functools import partial
from typing import Any

import gradio as gr

from adetailer import AFTER_DETAILER
from adetailer.args import AD_ENABLE, ALL_ARGS, MASK_MERGE_INVERT
from controlnet_ext import controlnet_exists, get_cn_inpaint_models


class Widgets:
    def tolist(self):
        return [getattr(self, attr) for attr in ALL_ARGS.attrs]


def gr_interactive(value: bool = True):
    return gr.update(interactive=value)


def ordinal(n: int) -> str:
    d = {1: "st", 2: "nd", 3: "rd"}
    return str(n) + ("th" if 11 <= n % 100 <= 13 else d.get(n % 10, "th"))


def suffix(n: int, c: str = " ") -> str:
    return "" if n == 0 else c + ordinal(n + 1)


def on_widget_change(state: dict, value: Any, *, attr: str):
    state[attr] = value
    return state


def on_generate_click(state: dict, *values: Any):
    for attr, value in zip(ALL_ARGS.attrs, values):
        state[attr] = value
    return state


def adui(
    num_models: int,
    is_img2img: bool,
    model_list: list[str],
    t2i_button: gr.Button,
    i2i_button: gr.Button,
):
    states = []
    infotext_fields = []

    with gr.Accordion(AFTER_DETAILER, open=False, elem_id="AD_main_acc"):
        with gr.Row():
            ad_enable = gr.Checkbox(
                label="Enable ADetailer",
                value=False,
                visible=True,
            )

        infotext_fields.append((ad_enable, AD_ENABLE.name))

        with gr.Group(), gr.Tabs():
            for n in range(num_models):
                with gr.Tab(ordinal(n + 1)):
                    state, infofields = one_ui_group(
                        n=n,
                        is_img2img=is_img2img,
                        model_list=model_list,
                        t2i_button=t2i_button,
                        i2i_button=i2i_button,
                    )

                states.append(state)
                infotext_fields.extend(infofields)

    # components: [bool, dict, dict, ...]
    components = [ad_enable] + states
    return components, infotext_fields


def one_ui_group(
    n: int,
    is_img2img: bool,
    model_list: list[str],
    t2i_button: gr.Button,
    i2i_button: gr.Button,
):
    w = Widgets()
    state = gr.State({})

    with gr.Row():
        model_choices = model_list if n == 0 else ["None"] + model_list

        w.ad_model = gr.Dropdown(
            label="ADetailer model" + suffix(n),
            choices=model_choices,
            value=model_choices[0],
            visible=True,
            type="value",
        )

    with gr.Group():
        with gr.Row(elem_id="AD_toprow_prompt" + suffix(n, "_")):
            w.ad_prompt = gr.Textbox(
                label="ad_prompt" + suffix(n),
                show_label=False,
                lines=3,
                placeholder="ADetailer prompt" + suffix(n),
                elem_id="AD_prompt" + suffix(n, "_"),
            )

        with gr.Row(elem_id="AD_toprow_negative_prompt" + suffix(n, "_")):
            w.ad_negative_prompt = gr.Textbox(
                label="ad_negative_prompt" + suffix(n),
                show_label=False,
                lines=2,
                placeholder="ADetailer negative prompt" + suffix(n),
                elem_id="AD_negative_prompt" + suffix(n, "_"),
            )

    with gr.Group():
        with gr.Accordion("Detection", open=False):
            detection(w, n)
        with gr.Accordion("Mask Preprocessing", open=False):
            mask_preprocessing(w, n)
        with gr.Accordion("Inpainting", open=False):
            inpainting(w, n)

    with gr.Group(), gr.Row(variant="panel"):
        cn_inpaint_models = ["None"] + get_cn_inpaint_models()

        w.ad_controlnet_model = gr.Dropdown(
            label="ControlNet model" + suffix(n),
            choices=cn_inpaint_models,
            value="None",
            visible=True,
            type="value",
            interactive=controlnet_exists,
        )

        w.ad_controlnet_weight = gr.Slider(
            label="ControlNet weight" + suffix(n),
            minimum=0.0,
            maximum=1.0,
            step=0.05,
            value=1.0,
            visible=True,
            interactive=controlnet_exists,
        )

    for attr in ALL_ARGS.attrs:
        widget = getattr(w, attr)
        on_change = partial(on_widget_change, attr=attr)
        widget.change(
            fn=on_change, inputs=[state, widget], outputs=[state], queue=False
        )

    all_inputs = [state] + w.tolist()
    target_button = i2i_button if is_img2img else t2i_button
    target_button.click(
        fn=on_generate_click, inputs=all_inputs, outputs=state, queue=False
    )

    infotext_fields = [(getattr(w, attr), name + suffix(n)) for attr, name in ALL_ARGS]

    return state, infotext_fields


def detection(w: Widgets, n: int):
    with gr.Row():
        with gr.Column():
            w.ad_conf = gr.Slider(
                label="Detection model confidence threshold %" + suffix(n),
                minimum=0,
                maximum=100,
                step=1,
                value=30,
                visible=True,
            )

        with gr.Column(variant="compact"):
            w.ad_mask_min_ratio = gr.Slider(
                label="Mask min area ratio" + suffix(n),
                minimum=0.0,
                maximum=1.0,
                step=0.001,
                value=0.0,
                visible=True,
            )
            w.ad_mask_max_ratio = gr.Slider(
                label="Mask max area ratio" + suffix(n),
                minimum=0.0,
                maximum=1.0,
                step=0.001,
                value=1.0,
                visible=True,
            )


def mask_preprocessing(w: Widgets, n: int):
    with gr.Group():
        with gr.Row():
            with gr.Column(variant="compact"):
                w.ad_x_offset = gr.Slider(
                    label="Mask x(→) offset" + suffix(n),
                    minimum=-200,
                    maximum=200,
                    step=1,
                    value=0,
                    visible=True,
                )
                w.ad_y_offset = gr.Slider(
                    label="Mask y(↑) offset" + suffix(n),
                    minimum=-200,
                    maximum=200,
                    step=1,
                    value=0,
                    visible=True,
                )

            with gr.Column(variant="compact"):
                w.ad_dilate_erode = gr.Slider(
                    label="Mask erosion (-) / dilation (+)" + suffix(n),
                    minimum=-128,
                    maximum=128,
                    step=4,
                    value=32,
                    visible=True,
                )

        with gr.Row():
            w.ad_mask_merge_invert = gr.Radio(
                label="Mask merge mode" + suffix(n),
                choices=MASK_MERGE_INVERT,
                value="None",
            )


def inpainting(w: Widgets, n: int):
    with gr.Group():
        with gr.Row():
            w.ad_mask_blur = gr.Slider(
                label="Inpaint mask blur" + suffix(n),
                minimum=0,
                maximum=64,
                step=1,
                value=4,
                visible=True,
            )

            w.ad_denoising_strength = gr.Slider(
                label="Inpaint denoising strength" + suffix(n),
                minimum=0.0,
                maximum=1.0,
                step=0.01,
                value=0.4,
                visible=True,
            )

        with gr.Row():
            with gr.Column(variant="compact"):
                w.ad_inpaint_full_res = gr.Checkbox(
                    label="Inpaint at full resolution " + suffix(n),
                    value=True,
                    visible=True,
                )
                w.ad_inpaint_full_res_padding = gr.Slider(
                    label="Inpaint at full resolution padding, pixels " + suffix(n),
                    minimum=0,
                    maximum=256,
                    step=4,
                    value=0,
                    visible=True,
                )

                w.ad_inpaint_full_res.change(
                    gr_interactive,
                    inputs=w.ad_inpaint_full_res,
                    outputs=w.ad_inpaint_full_res_padding,
                    queue=False,
                )

            with gr.Column(variant="compact"):
                w.ad_use_inpaint_width_height = gr.Checkbox(
                    label="Use separate width/height" + suffix(n),
                    value=False,
                    visible=True,
                )

                w.ad_inpaint_width = gr.Slider(
                    label="inpaint width" + suffix(n),
                    minimum=64,
                    maximum=2048,
                    step=4,
                    value=512,
                    visible=True,
                )

                w.ad_inpaint_height = gr.Slider(
                    label="inpaint height" + suffix(n),
                    minimum=64,
                    maximum=2048,
                    step=4,
                    value=512,
                    visible=True,
                )

                w.ad_use_inpaint_width_height.change(
                    lambda value: (gr_interactive(value), gr_interactive(value)),
                    inputs=w.ad_use_inpaint_width_height,
                    outputs=[w.ad_inpaint_width, w.ad_inpaint_height],
                    queue=False,
                )

        with gr.Row():
            with gr.Column(variant="compact"):
                w.ad_use_steps = gr.Checkbox(
                    label="Use separate steps" + suffix(n),
                    value=False,
                    visible=True,
                )

                w.ad_steps = gr.Slider(
                    label="ADetailer steps" + suffix(n),
                    minimum=1,
                    maximum=150,
                    step=1,
                    value=28,
                    visible=True,
                )

                w.ad_use_steps.change(
                    gr_interactive,
                    inputs=w.ad_use_steps,
                    outputs=w.ad_steps,
                    queue=False,
                )

            with gr.Column(variant="compact"):
                w.ad_use_cfg_scale = gr.Checkbox(
                    label="Use separate CFG scale" + suffix(n),
                    value=False,
                    visible=True,
                )

                w.ad_cfg_scale = gr.Slider(
                    label="ADetailer CFG scale" + suffix(n),
                    minimum=0.0,
                    maximum=30.0,
                    step=0.5,
                    value=7.0,
                    visible=True,
                )

                w.ad_use_cfg_scale.change(
                    gr_interactive,
                    inputs=w.ad_use_cfg_scale,
                    outputs=w.ad_cfg_scale,
                    queue=False,
                )

        with gr.Row():
            w.ad_restore_face = gr.Checkbox(
                label="Restore faces after ADetailer" + suffix(n),
                value=False,
            )
