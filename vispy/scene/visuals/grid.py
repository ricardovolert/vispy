# -*- coding: utf-8 -*-
# Copyright (c) 2014, Vispy Development Team.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.

from __future__ import division

import numpy as np

from ... import gloo
from ...gloo import gl
from ..transforms import STTransform, NullTransform
from .visual import Visual
from ..shaders import ModularProgram


VERT = """
attribute vec2 pos;
varying vec4 v_pos;
void main() {
    v_pos = vec4(pos, 0, 1);
    gl_Position = v_pos;
}
"""

FRAG = """
varying vec4 v_pos;
uniform vec2 scale; 

void main() {
    vec4 px_pos = $map_nd_to_canvas(v_pos);
    
    // Compute vectors representing width, height of pixel in local coords
    float s = 1.;
    vec4 local_pos = $map_canvas_to_local(px_pos);
    vec4 dx = $map_canvas_to_local(px_pos + vec4(1.0 / s, 0, 0, 0)) - local_pos;
    vec4 dy = $map_canvas_to_local(px_pos + vec4(0, 1.0 / s, 0, 0)) - local_pos;
    
    // Pixel length along each axis, rounded to the nearest power of 10
    vec2 px = s * vec2(abs(dx.x) + abs(dy.x), abs(dx.y) + abs(dy.y));
    float log10 = log(10.0);
    float sx = pow(10.0, floor(log(px.x) / log10)+1) * scale.x;
    float sy = pow(10.0, floor(log(px.y) / log10)+1) * scale.y;
    
    float x_alpha;
    if (mod(local_pos.x, 100 * sx) < px.x) {
        x_alpha = clamp(1 * sx/px.x, 0, 0.4);
    }
    else if (mod(local_pos.x, 10 * sx) < px.x) {
        x_alpha = clamp(0.1 * sx/px.x, 0, 0.4);
    }
    
    float y_alpha;
    if (mod(local_pos.y, 100 * sy) < px.y) {
        y_alpha = clamp(1 * sy/px.y, 0, 0.4);
    }
    else if (mod(local_pos.y, 10 * sy) < px.y) {
        y_alpha = clamp(0.1 * sy/px.y, 0, 0.4);
    }
    
    gl_FragColor = vec4(1, 1, 1, max(x_alpha, y_alpha));
}
"""

class Grid(Visual):
    """
    """
    def __init__(self, scale=(1, 1), **kwds):
        super(Visual, self).__init__(**kwds)
        self._program = ModularProgram(VERT, FRAG)
        self._vbo = None
        self._scale = scale

    def _buffer(self):
        if self._vbo is None:
            # quad covers entire view; frag. shader will deal with image shape
            quad = np.array([[-1, -1, 0], [1, -1, 0], [1, 1, 0],
                             [-1, -1, 0], [1, 1, 0], [-1, 1, 0]],
                            dtype=np.float32)
            self._vbo = gloo.VertexBuffer(quad)
        return self._vbo

    def draw(self, event):
        gloo.set_state('translucent', cull_face='front_and_back')

        canvas_to_ndc = event.entity_transform(map_from=event.canvas.entity, 
                                              map_to=event.ndc)
        local_to_canvas = event.canvas_transform()
        
        self._program.frag['map_nd_to_canvas'] = canvas_to_ndc.shader_imap()
        self._program.frag['map_canvas_to_local'] = local_to_canvas.shader_imap()
        self._program.prepare()
        self._program['pos'] = self._buffer()
        self._program['scale'] = self._scale
        self._program.draw('triangles')
