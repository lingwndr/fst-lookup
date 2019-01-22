#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 Eddie Antonio Santos <easantos@ualberta.ca>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
from collections import namedtuple
from enum import Enum
from pathlib import Path
from typing import Union, Tuple, List, Set, Iterable


PathLike = Union[str, Path]


class FST:
    def lookup(self, surface_form: str) -> Iterable[Tuple[str, ...]]:
        yield from []

    @classmethod
    def from_file(self, path: PathLike) -> 'FST':
        ...
    
    @classmethod
    def from_text(self, att_text: str) -> 'FST':
        parse = parse_text(att_text)
        return FST()

# TODO: namedtuple for arc
class FSTParse(namedtuple('FSTParse', 'multichar_symbols graphemes '
                                      'arcs '
                                      'intermediate_states accepting_states')):
    """
    The parsed data from an FST, in a nice neat pile.
    """

    @property
    def sigma(self):
        return {**self.multichar_symbols, **self.graphemes}

    @property
    def states(self):
        return self.intermediate_states | self.accepting_states


class Arc(namedtuple('ArcBase', 'state in_label out_label destination')):
    """
    An arc (transition) in the FST.
    """
    def __str__(self) -> str:
        return '{:d} -{:s}:{:s}→ {:d}'.format(
                self.state,
                self.in_label,
                self.out_label,
                self.destination
        )


def parse_text(fst_text: str) -> FSTParse:
    class ParserState:
        INITIAL = 0
        PROPS = 1
        SIGMA = 2
        ARC = 3
        END = 4

    def parse_arc(arc_def: Tuple[int, ...]) -> None:
        """
        Either:
          - appends an arc to the list;
          - adds an accepting state; or
          - finds the sentinel value
        """
        nonlocal implied_state

        if arc_def == (-1, -1, -1, -1, -1):
            # Sentinel value: there are no more arcs to define.
            return

        if len(arc_def) == 2:
            if implied_state is None:
                raise ValueError('No implied state')
            src = implied_state
            in_label, dest = arc_def
            out_label = in_label
        elif len(arc_def) == 3:
            if implied_state is None:
                raise ValueError('No implied state')
            src = implied_state
            in_label, out_label, dest = arc_def
        elif len(arc_def) == 4:
            src, in_label, dest, _weight = arc_def
            out_label = in_label
            if in_label == -1 or dest == -1:
                # This is an accepting state
                accepting_states.add(src)
                return
        elif len(arc_def) == 5:
            src, in_label, out_label, dest, _weight = arc_def

        implied_state = src
        arcs.append(Arc(src, dest, in_label, out_label))

    state = ParserState.INITIAL

    # Start with an empty FST
    sigma = {}
    arcs = []  # type: List[Arc]
    accepting_states = set()  # type: Set[int]
    implied_state = None

    for line in fst_text.splitlines():
        # Check header
        if line.startswith('##'):
            header = line[2:-2]
            state = {
                'foma-net 1.0': ParserState.INITIAL,
                'props': ParserState.PROPS,
                'sigma': ParserState.SIGMA,
                'states': ParserState.ARC,
                'end': ParserState.END,
            }[header]
        elif state == ParserState.SIGMA:
            # Add an entry to sigma
            idx_str, symbol = line.split()
            idx = int(idx_str)
            sigma[idx] = symbol
        elif state == ParserState.ARC:
            # Add an arc
            arc_def = tuple(int(x) for x in line.split())
            parse_arc(arc_def)
        elif state in (ParserState.INITIAL, ParserState.PROPS, ParserState.END):
            pass  # Nothing to do for these states
        else:
            raise ValueError('Invalid state: ' + repr(state))

    # After parsing, we should be in the ##end## state.
    assert state == ParserState.END

    # Get rid of epsilon (it is always assumed!)
    del sigma[0]

    multichar_symbols = {idx: symbol for idx, symbol in sigma.items()
                         if len(symbol) > 1}
    graphemes = {idx: symbol for idx, symbol in sigma.items()
                 if len(symbol) == 1}

    states = {arc.state for arc in arcs}

    return FSTParse(multichar_symbols=multichar_symbols,
                    graphemes=graphemes,
                    arcs=set(arcs),
                    intermediate_states=states,
                    accepting_states=accepting_states)
