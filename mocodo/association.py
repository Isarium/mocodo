#!/usr/bin/env python
# encoding: utf-8

from __future__ import division

import re
from math import sqrt

from .attribute import *
from .leg import *
from .dynamic import Dynamic
from .mocodo_error import MocodoError

match_leg = re.compile(r"((?:_11|..)[<>]?\s+(?:\[.+?\]\s+)?)(.+)").match

TRIANGLE_ALTITUDE = sqrt(3) / 2
INCIRCLE_RADIUS = 1 / sqrt(12)

class Association:

    def __init__(self, clause, params={"df": u"DF", "card_format": u"{min_card},{max_card}"}):
        def clean_up(name, legs, attributes):
            name = name.strip()
            is_inheritance = False
            if name.startswith("/") and name.endswith("\\"):
                name = name[1:-1]
                is_inheritance = True
            cartouche = (name[:-1] if name[-1:].isdigit() else name)
            (cards, entities) = ([], [])
            l = []
            for leg in legs.split(","):
                leg = leg.strip()
                m = match_leg(leg)
                if m:
                    l.append(m.groups())
                else:
                    raise MocodoError(2, _('Missing cardinalities in leg "{leg}" of association "{association}".').format(leg=leg, association=name))
            (cards, entities) = zip(*l)
            return (name, cartouche, list(cards), list(entities), outer_split(attributes), is_inheritance)

        (name, legs_and_attributes) = clause.split(",", 1)
        (legs, attributes) = (legs_and_attributes.split(":", 1) + [""])[:2]
        (self.name, self.cartouche, cards, entities, attributes, is_inheritance) = clean_up(name, legs, attributes)
        self.attributes = [SimpleAssociationAttribute(attribute, i) for (i, attribute) in enumerate(attributes)]
        entities = [(e.strip(), entities.count(e), entities[:i].count(e)) for (i, e) in enumerate(entities)]
        self.df_label = params["df"]
        if self.cartouche == self.df_label:
            association_type = "df"
            self.kind = "association"
        elif is_inheritance:
            association_type = "inheritance"
            self.kind = "inheritance"
            if cards and cards[0][2:3] not in [">", "<"]:
                cards[0] = cards[0][:2] + ">" + cards[0][2:]
        else:
            association_type = "default"
            self.kind = "association"
        self.set_association_type_strategy(association_type)
        self.clause = clause
        self.legs = []
        for (card, (entity, count, num)) in zip(cards, entities):
            leg = Leg(self, card, entity, params)
            leg.set_spin_strategy(0 if count == 1 else 2 * num / (count - 1) - 1)
            self.legs.append(leg)

    def calculate_size(self, style, get_font_metrics):
        self.style = style
        cartouche_font = get_font_metrics(style["association_cartouche_font"])
        self.get_cartouche_string_width = cartouche_font.get_pixel_width
        self.cartouche_height = cartouche_font.get_pixel_height()
        attribute_font = get_font_metrics(style["association_attribute_font"])
        self.attribute_height = attribute_font.get_pixel_height()
        self.calculate_size_depending_on_df(get_font_metrics)
        self.w += self.w % 2
        self.h += self.h % 2
        for leg in self.legs:
            leg.calculate_size(style, get_font_metrics)

    def set_association_type_strategy(self, association_type):

        def calculate_size_when_df(get_font_metrics):
            self.w = self.h = max(
                self.style["round_rect_margin_width"] * 2 + self.get_cartouche_string_width(self.df_label),
                self.style["round_rect_margin_width"] * 2 + self.cartouche_height
            )

        def calculate_size_when_inheritance(get_font_metrics):
            self.w = self.h = max(
                self.style["round_rect_margin_width"] * 2 + self.cartouche_height * 2,
                self.style["round_rect_margin_width"] * 2 + self.cartouche_height * 2
            )

        def calculate_size_when_default(get_font_metrics):
            for attribute in self.attributes:
                attribute.calculate_size(self.style, get_font_metrics)
            cartouche_and_attribute_widths = [a.w for a in self.attributes] + [self.get_cartouche_string_width(self.cartouche)]
            self.w = 2 * self.style["round_rect_margin_width"] + max(cartouche_and_attribute_widths)
            self.h = max(1, len(self.attributes)) * (self.attribute_height + self.style["line_skip_height"]) \
                - self.style["line_skip_height"] \
                + 2 * self.style["rect_margin_height"] \
                + 2 * self.style["round_rect_margin_height"] \
                + self.cartouche_height
            self.w += self.w % 2
            self.h += self.h % 2

        def description_when_df():
            return [
                {
                    "key": "stroke_depth",
                    "stroke_depth": self.style["box_stroke_depth"],
                },
                {
                    "key": "stroke_color",
                    "stroke_color": Dynamic("colors['association_stroke_color']"),
                },
                {
                    "key": "color",
                    "color": Dynamic("colors['association_cartouche_color']"),
                },
                {
                    "key": "circle",
                    "cx": Dynamic("x"),
                    "cy": Dynamic("y"),
                    "r": self.w // 2,
                },
                {
                    "key": "text",
                    "text": self.df_label,
                    "text_color": Dynamic("colors['association_cartouche_text_color']"),
                    "x": Dynamic("%s+x" % (self.style["round_rect_margin_width"] - self.w // 2)),
                    "y": Dynamic("%s+y" % round(self.style["round_rect_margin_height"] - self.h / 2 + self.style["df_text_height_ratio"] * self.cartouche_height, 1)),
                    "family": self.style["association_cartouche_font"]["family"],
                    "size": self.style["association_cartouche_font"]["size"],
                },
            ]

        def description_when_inheritance():
            return [
                {
                    "key": "stroke_depth",
                    "stroke_depth": self.style["box_stroke_depth"],
                },
                {
                    "key": "stroke_color",
                    "stroke_color": Dynamic("colors['association_stroke_color']"),
                },
                {
                    "key": "color",
                    "color": Dynamic("colors['association_cartouche_color']"),
                },
                {
                    "key": "triangle",
                    "x1": Dynamic("x"),
                    "x2": Dynamic("x-%s" % (self.w // 2)),
                    "x3": Dynamic("x+%s" % (self.w // 2)),
                    "y1": Dynamic("y-%s" % ((TRIANGLE_ALTITUDE - INCIRCLE_RADIUS) * self.w)),
                    "y2": Dynamic("y+%s" % (INCIRCLE_RADIUS * self.w)),
                    "y3": Dynamic("y+%s" % (INCIRCLE_RADIUS * self.w)),
                },
                {
                    "key": "text",
                    "text": self.cartouche,
                    "text_color": Dynamic("colors['association_cartouche_text_color']"),
                    "x": Dynamic("%s+x" % (-self.get_cartouche_string_width(self.cartouche) // 2)),
                    "y": Dynamic("y+%s" % (self.cartouche_height // 3)),
                    "family": self.style["association_cartouche_font"]["family"],
                    "size": self.style["association_cartouche_font"]["size"],
                },
            ]

        def description_when_default():
            result = [
                {
                    "key": "stroke_depth",
                    "stroke_depth": 0,
                },
                {
                    "key": "stroke_color",
                    "stroke_color": Dynamic("colors['association_cartouche_color']"),
                },
                {
                    "key": "color",
                    "color": Dynamic("colors['association_cartouche_color']"),
                },
                {
                    "key": "upper_round_rect",
                    "radius": self.style["round_corner_radius"],
                    "x": Dynamic("%s+x" % (-self.w // 2)),
                    "y": Dynamic("%s+y" % (-self.h // 2)),
                    "w": self.w,
                    "h": self.attribute_height + self.style["round_rect_margin_height"] + self.style["rect_margin_height"],
                },
                {
                    "key": "stroke_color",
                    "stroke_color": Dynamic("colors['association_color']"),
                },
                {
                    "key": "color",
                    "color": Dynamic("colors['association_color']"),
                },
                {
                    "key": "lower_round_rect",
                    "radius": self.style["round_corner_radius"],
                    "x": Dynamic("%s+x" % (-self.w // 2)),
                    "y": Dynamic("%s+y" % round(self.attribute_height + self.style["round_rect_margin_height"] + self.style["rect_margin_height"] - self.h / 2, 1)),
                    "w": self.w,
                    "h": self.h - (self.attribute_height + self.style["round_rect_margin_height"] + self.style["rect_margin_height"]),
                },
                {
                    "key": "color",
                    "color": Dynamic("colors['transparent_color']"),
                },
                {
                    "key": "stroke_color",
                    "stroke_color": Dynamic("colors['association_stroke_color']"),
                },
                {
                    "key": "stroke_depth",
                    "stroke_depth": self.style["box_stroke_depth"],
                },
                {
                    "key": "round_rect",
                    "radius": self.style["round_corner_radius"],
                    "x": Dynamic("%s+x" % (-self.w // 2)),
                    "y": Dynamic("%s+y" % (-self.h // 2)),
                    "w": self.w,
                    "h": self.h,
                },
                {
                    "key": "stroke_depth",
                    "stroke_depth": self.style["inner_stroke_depth"],
                },
                {
                    "key": "line",
                    "x0": Dynamic("%s+x" % (-self.w // 2)),
                    "y0": Dynamic("%s+y" % (self.attribute_height + self.style["round_rect_margin_height"] + self.style["rect_margin_height"] - self.h // 2)),
                    "x1": Dynamic("%s+x" % (self.w // 2)),
                    "y1": Dynamic("%s+y" % (self.attribute_height + self.style["round_rect_margin_height"] + self.style["rect_margin_height"] - self.h // 2)),
                },
                {
                    "key": "text",
                    "text": self.cartouche,
                    "text_color": Dynamic("colors['association_cartouche_text_color']"),
                    "x": Dynamic("%s+x" % (-self.get_cartouche_string_width(self.cartouche) // 2)),
                    "y": Dynamic("%s+y" % round(-self.h / 2 + self.style["rect_margin_height"] + self.style["cartouche_text_height_ratio"] * self.cartouche_height, 1)),
                    "family": self.style["association_cartouche_font"]["family"],
                    "size": self.style["association_cartouche_font"]["size"],
                }
            ]
            dx = self.style["round_rect_margin_width"] - self.w // 2
            dy = self.style["round_rect_margin_height"] + self.cartouche_height + 2 * self.style["rect_margin_height"] - self.h // 2
            for attribute in self.attributes:
                attribute.name = self.name
                result.extend(attribute.description(dx, dy))
                dy += self.attribute_height + self.style["line_skip_height"]
            return result

        if association_type == "df":
            self.calculate_size_depending_on_df = calculate_size_when_df
            self.description_depending_on_df = description_when_df
        elif association_type == "inheritance":
            self.calculate_size_depending_on_df = calculate_size_when_inheritance
            self.description_depending_on_df = description_when_inheritance
        else:
            self.calculate_size_depending_on_df = calculate_size_when_default
            self.description_depending_on_df = description_when_default

    def set_df_label(self, df_label):
        self.set_df_label_depending_on_df(df_label)

    def description(self):
        return self.leg_descriptions() + [
            {
                "key": "begin",
                "id": u"association-%s" % self.name,
            },
        ] + self.description_depending_on_df() + [
            {
                "key": "end",
            },
        ]

    def leg_descriptions(self):
        result = [
            "Association %s" % self.name,
            {
                "key": "env",
                "env": [("x", """cx[u"%s"]""" % self.name), ("y", """cy[u"%s"]""" % self.name)],
            },
        ]
        for leg in self.legs:
            result.extend(leg.description())
        return result

    def leg_identifiers(self):
        for leg in self.legs:
            yield leg.identifier
