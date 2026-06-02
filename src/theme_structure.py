THEME_STRUCTURE = {

    "Windows (not the OS but the UI elements)": {
        "Windows": {

            "sections": {

                "windows": {
                    "background-color": {
                        "label": "Window background color",
                        "selector": "window",
                        "type": "color",
                        "default": "#ffffff"
                    },

                    "color": {
                        "label": "Window text color",
                        "selector": "window",
                        "type": "color",
                        "default": "#000000"
                    }
                }
            }
        }
    },


    "Buttons": {

        "normal Buttons": {

            "sections": {

                "Buttons": {

                    "background-color": {
                        "label": "Button background color",
                        "selector": "button",
                        "type": "color",
                        "default": "#3584e4"
                    },

                    "color": {
                        "label": "Button text color",
                        "selector": "button",
                        "type": "color",
                        "default": "#ffffff"
                    },

                    "padding": {
                        "label": "Button padding",
                        "selector": "button",
                        "type": "double-int",
                        "min": 0,
                        "max": 15,
                        "default": [3, 8],
                        "unit": "px"
                    },

                    "min-height": {
                        "label": "Button min height",
                        "selector": "button",
                        "type": "slider",
                        "min": 0,
                        "max": 50,
                        "step": 1,
                        "default": 20,
                        "unit": "px"
                    },

                    "min-width": {
                        "label": "Button min width",
                        "selector": "button",
                        "type": "slider",
                        "min": 0,
                        "max": 50,
                        "step": 1,
                        "default": 20,
                        "unit": "px"
                    }
                },

                "Button border": {

                    "border": {
                        "label": "Button border",
                        "selector": "button",
                        "type": ["int", "enum"],
                        "min": 1,
                        "max": 15,
                        "default": [3, "solid"],
                        "unit": "px",
                        "options": ["solid", "dashed", "dotted"]
                    },

                    "border-color": {
                        "label": "Button border color",
                        "selector": "button",
                        "type": "color",
                        "default": "#3584e4"
                    },

                    "border-radius": {
                        "label": "Button border radius",
                        "selector": "button",
                        "type": "slider",
                        "min": 0,
                        "max": 25,
                        "step": 1,
                        "default": 5,
                        "unit": "px"
                    }
                }
            }
        }
    }
}