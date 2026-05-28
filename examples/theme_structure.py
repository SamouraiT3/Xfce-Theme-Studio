THEME_STRUCTURE = {
    "test de l'interface": {

        "example 1": {

            "sections": {

                "section1": {

                    "parameter1": {
                        "label": "item 1 with color type",
                        "selector": "the selector for the property",
                        "type": "color",
                        "default": "#3584e4"
                    },

                    "parameter2": {
                        "label": "item 2 with double-color type",
                        "selector": "the selector for the property",
                        "type": "double-color",
                        "default": ["#27A538", "#ffffff"]
                    },

                    "parameter3": {
                        "label": "item 3 with int type",
                        "selector": "the selector for the property",
                        "type": "int",
                        "default": 8,
                        "min": 0,
                        "max": 64,
                        "unit": "px"
                    },

                    "parameter4": {
                        "label": "item 4 with double-int type",
                        "selector": "the selector for the property",
                        "type": "double-int",
                        "default": [6, 8],
                        "min": 0,
                        "max": 30,
                        "unit": "px"
                    },

                    "parameter5": {
                        "label": "item 5 with slider type",
                        "selector": "the selector for the property",
                        "type": "slider",
                        "default": 50,
                        "min": 0,
                        "max": 100,
                        "unit": "%"
                    },

                    "parameter6": {
                        "label": "item 6 with double-slider type",
                        "selector": "the selector for the property",
                        "type": "double-slider",
                        "default": [25, 75],
                        "min": 0,
                        "max": 100,
                        "unit": "%",
                        "step": 1
                    }
                },

                "section2": {

                    "parameter7": {
                        "label": "item 1 with enum type",
                        "selector": "the selector for the property",
                        "type": "enum",
                        "options": ["option 1", "option 2", "option 3"],
                        "default": "option 1"
                    },

                    "parameter8": {
                        "label": "item 2 with double-enum type",
                        "selector": "the selector for the property",
                        "type": "double-enum",
                        "options": ["option 1", "option 2", "option 3"],
                        "default": ["option 1", "option 2"]
                    },

                    "parameter9": {
                        "label": "item 3 with bool type",
                        "selector": "the selector for the property",
                        "type": "bool",
                        "default": True
                    },

                    "parameter10": {
                        "label": "item 4 with double-bool type",
                        "selector": "the selector for the property",
                        "type": "double-bool",
                        "default": [True, False]
                    },

                    "parameter11": {
                        "label": "item 5 with int type",
                        "selector": "the selector for the property",
                        "type": "int",
                        "default": 2,
                        "min": 0,
                        "max": 10,
                        "unit": "px"
                    },

                    "parameter12": {
                        "label": "item 6 with double-int type",
                        "selector": "the selector for the property",
                        "type": "double-int",
                        "default": [5, 10],
                        "min": 0,
                        "max": 50,
                        "unit": "px"
                    }
                },
            },
        },

        "example 2": {

            "sections": {

                "single section (hidden because it's the only one)": {

                    "parameter1": {
                        "label": "item 1 with color type",
                        "selector": "the selector for the property",
                        "type": "color",
                        "default": "#3584e4"
                    },

                    "parameter2": {
                        "label": "item 2 with slider type",
                        "selector": "the selector for the property",
                        "type": "slider",
                        "default": 75,
                        "min": 0,
                        "max": 100,
                        "unit": "%"
                    },

                    "parameter3": {
                        "label": "item 3 with double-slider type",
                        "selector": "the selector for the property",
                        "type": "double-slider",
                        "default": [0.25, 0.75],
                        "min": 0.0,
                        "max": 1.0,
                        "step": 0.01
                    },

                    "parameter4": {
                        "label": "item 4 with enum type",
                        "selector": "the selector for the property",
                        "type": "enum",
                        "options": ["option 1", "option 2"],
                        "default": "option 1"
                    },

                    "parameter5": {
                        "label": "item 5 with bool type",
                        "selector": "the selector for the property",
                        "type": "bool",
                        "default": False
                    },
                },
            },
        },
    },
}