import bpy
import bgl
import blf
from bpy.types import BoolProperty
import math
from itertools import chain
from .decorators import blender_version

from .maths import Point2D,Vec2D

def set_cursor(cursor):
    # DEFAULT, NONE, WAIT, CROSSHAIR, MOVE_X, MOVE_Y, KNIFE, TEXT,
    # PAINT_BRUSH, HAND, SCROLL_X, SCROLL_Y, SCROLL_XY, EYEDROPPER
    for wm in bpy.data.window_managers:
        for win in wm.windows:
            win.cursor_modal_set(cursor)



class Drawing:
    _instance = None
    _dpi = 72
    _dpi_mult = 1
    
    @blender_version('<=', '2.78')
    @staticmethod
    def update_dpi():
        Drawing._dpi = bpy.context.user_preferences.system.dpi
        if bpy.context.user_preferences.system.virtual_pixel_mode == 'DOUBLE':
            Drawing._dpi *= 2
        Drawing._dpi *= bpy.context.user_preferences.system.pixel_size
        Drawing._dpi = int(Drawing._dpi)
        Drawing._dpi_mult = Drawing._dpi / 72
    
    @blender_version('>=', '2.79')
    @staticmethod
    def update_dpi():
        Drawing._dpi = 72 # bpy.context.user_preferences.system.dpi
        Drawing._dpi *= bpy.context.user_preferences.view.ui_scale
        Drawing._dpi *= bpy.context.user_preferences.system.pixel_size
        Drawing._dpi = int(Drawing._dpi)
        Drawing._dpi_mult = bpy.context.user_preferences.view.ui_scale * bpy.context.user_preferences.system.pixel_size
    
    @staticmethod
    def get_instance():
        Drawing.update_dpi()
        if not Drawing._instance:
            Drawing._creating = True
            Drawing._instance = Drawing()
            del Drawing._creating
        return Drawing._instance
    
    def __init__(self):
        assert hasattr(self, '_creating'), "Do not instantiate directly.  Use Drawing.get_instance()"
        
        self.font_id = 0
        self.text_size(12)
    
    def scale(self, s): return s * self._dpi_mult
    def unscale(self, s): return s / self._dpi_mult
    def get_dpi_mult(self): return self._dpi_mult
    def line_width(self, width): bgl.glLineWidth(self.scale(width))
    def point_size(self, size): bgl.glPointSize(self.scale(size))
    
    def text_size(self, size):
        blf.size(self.font_id, size, self._dpi)
        self.line_height = round(blf.dimensions(self.font_id, "XMPQpqjI")[1] + 3*self._dpi_mult)
        self.line_base = round(blf.dimensions(self.font_id, "XMPQI")[1])
    
    def get_text_size(self, text):
        size = blf.dimensions(self.font_id, text)
        return (round(size[0]), round(size[1]))
    def get_text_width(self, text):
        size = blf.dimensions(self.font_id, text)
        return round(size[0])
    def get_text_height(self, text):
        size = blf.dimensions(self.font_id, text)
        return round(size[1])
    def get_line_height(self, text=None):
        if not text: return self.line_height
        return self.line_height * (1 + text.count('\n'))
    
    def set_clipping(self, xmin, ymin, xmax, ymax):
        blf.clipping(self.font_id, xmin, ymin, xmax, ymax)
        self.enable_clipping()
    def enable_clipping(self):
        blf.enable(self.font_id, blf.CLIPPING)
    def disable_clipping(self):
        blf.disable(self.font_id, blf.CLIPPING)
    
    def text_draw2D(self, text, pos:Point2D, color, dropshadow=None):
        lines = str(text).split('\n')
        l,t = round(pos[0]),round(pos[1])
        lh = self.line_height
        lb = self.line_base
        
        if dropshadow: self.text_draw2D(text, (l+1,t-1), dropshadow)
        
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glColor4f(*color)
        for i,line in enumerate(lines):
            th = self.get_text_height(line)
            # x,y = l,t - (i+1)*lh + int((lh-th)/2)
            x,y = l,t - (i+1)*lh + int((lh-lb)/2+2*self._dpi_mult)
            blf.position(self.font_id, x, y, 0)
            blf.draw(self.font_id, line)
            y -= self.line_height
    
    def textbox_draw2D(self, text, pos:Point2D, padding=5, textbox_position=7):
        '''
        textbox_position specifies where the textbox is drawn in relation to pos.
        ex: if textbox_position==7, then the textbox is drawn where pos is the upper-left corner
        tip: textbox_position is arranged same as numpad
                    +-----+
                    |7 8 9|
                    |4 5 6|
                    |1 2 3|
                    +-----+
        '''
        lh = self.line_height
        
        # TODO: wrap text!
        lines = text.split('\n')
        w = max(self.get_text_width(line) for line in lines)
        h = len(lines) * lh
        
        # find top-left corner (adjusting for textbox_position)
        l,t = round(pos[0]),round(pos[1])
        textbox_position -= 1
        lcr = textbox_position % 3
        tmb = int(textbox_position / 3)
        l += [w+padding,round(w/2),-padding][lcr]
        t += [h+padding,round(h/2),-padding][tmb]
        
        bgl.glEnable(bgl.GL_BLEND)
        
        bgl.glColor4f(0.0, 0.0, 0.0, 0.25)
        bgl.glBegin(bgl.GL_QUADS)
        bgl.glVertex2f(l+w+padding,t+padding)
        bgl.glVertex2f(l-padding,t+padding)
        bgl.glVertex2f(l-padding,t-h-padding)
        bgl.glVertex2f(l+w+padding,t-h-padding)
        bgl.glEnd()
        
        bgl.glColor4f(0.0, 0.0, 0.0, 0.75)
        self.drawing.line_width(1.0)
        bgl.glBegin(bgl.GL_LINE_STRIP)
        bgl.glVertex2f(l+w+padding,t+padding)
        bgl.glVertex2f(l-padding,t+padding)
        bgl.glVertex2f(l-padding,t-h-padding)
        bgl.glVertex2f(l+w+padding,t-h-padding)
        bgl.glVertex2f(l+w+padding,t+padding)
        bgl.glEnd()
        
        bgl.glColor4f(1,1,1,0.5)
        for i,line in enumerate(lines):
            th = self.get_text_height(line)
            y = t - (i+1)*lh + int((lh-th) / 2)
            blf.position(self.font_id, l, y, 0)
            blf.draw(self.font_id, line)


class UI_Element:
    def __init__(self):
        self.drawing = Drawing.get_instance()
        self.dpi_mult = self.drawing.get_dpi_mult()
        self.context = bpy.context
        self.pos = None
        self.size = None
        self.margin = 4
    
    def __hover_ui(self, mouse):
        if not self.pos or not self.size: return None
        x,y = mouse
        l,t = self.pos
        w,h = self.size
        if x < l or x >= l + w: return None
        if y > t or y <= t - h: return None
        return self
    
    def hover_ui(self, mouse): return self.__hover_ui(mouse)
    
    def draw(self, left, top, width, height):
        m = self.margin
        self.pos = Point2D((left+m, top-m))
        self.size = Vec2D((width-m*2, height-m*2))
        self.predraw()
        #self.drawing.set_clipping(left, top-height, left+width, top)
        self._draw()
        #self.drawing.disable_clipping()
    
    def get_width(self): return self._get_width() + self.margin*2
    def get_height(self): return self._get_height() + self.margin*2
    
    def _get_width(self): return 0
    def _get_height(self): return 0
    def _draw(self): pass
    def predraw(self): pass
    def mouse_down(self, mouse): pass
    def mouse_move(self, mouse): pass
    def mouse_up(self, mouse): pass
    
    def mouse_cursor(self): return 'DEFAULT'


class UI_Spacer(UI_Element):
    def __init__(self, width=0, height=0):
        super().__init__()
        self.width = width
        self.height = height
        self.margin = 0
    def _get_width(self): return self.width * self.dpi_mult
    def _get_height(self): return self.height * self.dpi_mult


class UI_Label(UI_Element):
    def __init__(self, label, icon=None, tooltip=None, color=(1,1,1,1), bgcolor=None, align=-1):
        super().__init__()
        self.set_label(label)
        self.icon = icon
        self.tooltip = tooltip
        self.color = color
        self.align = align
        self.bgcolor = bgcolor
    
    def set_bgcolor(self, bgcolor): self.bgcolor = bgcolor
    
    def set_label(self, label):
        self.text = str(label)
        self.text_width = self.drawing.get_text_width(self.text)
        self.text_height = self.drawing.get_line_height(self.text)
    
    def _get_width(self): return self.text_width
    def _get_height(self): return self.text_height
    
    def _draw(self):
        l,t = self.pos
        w,h = self.size
        
        if self.bgcolor:
            bgl.glEnable(bgl.GL_BLEND)
            bgl.glColor4f(*self.bgcolor)
            bgl.glBegin(bgl.GL_QUADS)
            bgl.glVertex2f(l,t)
            bgl.glVertex2f(l,t-h)
            bgl.glVertex2f(l+w,t-h)
            bgl.glVertex2f(l+w,t)
            bgl.glEnd()
        
        if self.align < 0:
            self.drawing.text_draw2D(self.text, Point2D((l, t)), self.color)
        elif self.align == 0:
            self.drawing.text_draw2D(self.text, Point2D((l+(w-self.text_width)/2, t)), self.color)
        else:
            self.drawing.text_draw2D(self.text, Point2D((l+w-self.width, t)), self.color)



class UI_Rule(UI_Element):
    def __init__(self, thickness=2, padding=0, color=(1.0,1.0,1.0,0.25)):
        super().__init__()
        self.margin = 0
        self.thickness = thickness
        self.color = color
        self.padding = padding
    def _get_width(self): return self.dpi_mult * (self.padding*2 + 1)
    def _get_height(self): return self.dpi_mult * (self.padding*2 + self.thickness)
    def _draw(self):
        left,top = self.pos
        width,height = self.size
        t2 = round(self.thickness/2)
        padding = self.padding
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glColor4f(*self.color)
        self.drawing.line_width(self.thickness)
        bgl.glBegin(bgl.GL_LINES)
        bgl.glVertex2f(left+padding, top-padding-t2)
        bgl.glVertex2f(left+width-padding, top-padding-t2)
        bgl.glEnd()


class UI_Container(UI_Element):
    def __init__(self, vertical=True, background=None):
        super().__init__()
        self.vertical = vertical
        self.ui_items = []
        self.background = background
    
    def hover_ui(self, mouse):
        if not super().hover_ui(mouse): return None
        for ui in self.ui_items:
            hover = ui.hover_ui(mouse)
            if hover: return hover
        return self
    
    def _get_width(self):
        if not self.ui_items: return 0
        if self.vertical:
            return max(ui.get_width() for ui in self.ui_items)
        return sum(ui.get_width() for ui in self.ui_items)
    def _get_height(self):
        if not self.ui_items: return 0
        if self.vertical:
            return sum(ui.get_height() for ui in self.ui_items)
        return max(ui.get_height() for ui in self.ui_items)
    
    def _draw(self):
        l,t = self.pos
        w,h = self.size
        
        if self.background:
            bgl.glEnable(bgl.GL_BLEND)
            bgl.glColor4f(*self.background)
            bgl.glBegin(bgl.GL_QUADS)
            bgl.glVertex2f(l, t)
            bgl.glVertex2f(l+w, t)
            bgl.glVertex2f(l+w, t-h)
            bgl.glVertex2f(l, t-h)
            bgl.glEnd()
        
        if self.vertical:
            y = t
            for ui in self.ui_items:
                eh = ui.get_height()
                ui.draw(l,y,w,eh)
                y -= eh
        else:
            x = l
            l = len(self.ui_items)
            for i,ui in enumerate(self.ui_items):
                ew = ui.get_width() if i < l-1 else w
                ui.draw(x,t,ew,h)
                x += ew
                w -= ew
    
    def add(self, ui_item):
        self.ui_items.append(ui_item)
        return ui_item

class UI_EqualContainer(UI_Container):
    def __init__(self, vertical=True):
        super().__init__(vertical=vertical)
    
    def _draw(self):
        l,t = self.pos
        w,h = self.size
        if self.vertical:
            y = t
            eh = math.floor(h / len(self.ui_items))
            for ui in self.ui_items:
                ui.draw(l,y,w,eh)
                y -= eh
        else:
            x = l
            l = len(self.ui_items)
            ew = math.floor(w / len(self.ui_items))
            for i,ui in enumerate(self.ui_items):
                ui.draw(x,t,ew,h)
                x += ew
                w -= ew


class UI_Button(UI_Container):
    def __init__(self, label, fn_callback, icon=None, tooltip=None, color=(1,1,1,1), align=-1):
        super().__init__()
        self.add(UI_Label(label, icon=icon, tooltip=tooltip, color=color, align=align))
        self.fn_callback = fn_callback
        self.pressed = False
    
    def mouse_down(self, mouse):
        self.pressed = True
    def mouse_move(self, mouse):
        self.pressed = self.hover_ui(mouse) is not None
    def mouse_up(self, mouse):
        if self.pressed: self.fn_callback()
        self.pressed = False
    
    def hover_ui(self, mouse):
        return self if super().hover_ui(mouse) else None
    
    def mouse_cursor(self): return 'HAND'
    
    def _draw(self):
        l,t = self.pos
        w,h = self.size
        bgl.glEnable(bgl.GL_BLEND)
        self.drawing.line_width(1)
        bgl.glColor4f(0,0,0,0.1)
        
        if self.pressed:
            bgl.glBegin(bgl.GL_QUADS)
            bgl.glVertex2f(l,t)
            bgl.glVertex2f(l,t-h)
            bgl.glVertex2f(l+w,t-h)
            bgl.glVertex2f(l+w,t)
            bgl.glEnd()
        
        bgl.glBegin(bgl.GL_LINE_STRIP)
        bgl.glVertex2f(l,t)
        bgl.glVertex2f(l,t-h)
        bgl.glVertex2f(l+w,t-h)
        bgl.glVertex2f(l+w,t)
        bgl.glVertex2f(l,t)
        bgl.glEnd()
        super()._draw()
    




class UI_Options(UI_Container):
    def __init__(self, fn_callback):
        super().__init__()
        self.fn_callback = fn_callback
        self.options = {}
        self.selected = None
    
    def add_option(self, label, icon=None, tooltip=None, color=(1,1,1,1), align=-1):
        class UI_Option(UI_Container):
            def __init__(self, options, label, icon=None, tooltip=None, color=(1,1,1,1), align=-1):
                super().__init__(vertical=False)
                self.ui_label = UI_Label(label, tooltip=tooltip, color=color, align=align)
                self.ui_icon = icon
                # self.ui_label.margin = 4
                if self.ui_icon:
                    # self.ui_icon.margin = 4
                    self.add(self.ui_icon)
                    self.add(UI_Spacer(width=4))
                self.add(self.ui_label)
                self.margin = 0
                self.label = label
                self.options = options
            
            def hover_ui(self, mouse):
                return self if super().hover_ui(mouse) else None
            
            def _draw(self):
                if self.label == self.options.selected:
                    l,t = self.pos
                    w,h = self.size
                    bgl.glEnable(bgl.GL_BLEND)
                    bgl.glColor4f(0.27,0.50,0.72,0.90)
                    bgl.glBegin(bgl.GL_QUADS)
                    bgl.glVertex2f(l,t)
                    bgl.glVertex2f(l,t-h)
                    bgl.glVertex2f(l+w,t-h)
                    bgl.glVertex2f(l+w,t)
                    bgl.glEnd()
                super()._draw()
        
        option = UI_Option(self, label, icon=icon, tooltip=tooltip, color=color, align=align)
        super().add(option)
        self.options[option] = label
        if not self.selected: self.selected = label
    
    def set_option(self, label):
        if self.selected == label: return
        self.selected = label
        self.fn_callback(self.selected)
    
    def add(self, *args, **kwargs):
        assert False, "Do not call UI_Options.add()"
    
    def hover_ui(self, mouse):
        return self if super().hover_ui(mouse) else None
    
    def mouse_down(self, mouse): self.mouse_up(mouse)
    def mouse_move(self, mouse): self.mouse_up(mouse)
    def mouse_up(self, mouse):
        ui = super().hover_ui(mouse)
        if ui is None or ui == self: return
        self.set_option(self.options[ui])
    
    def _draw(self):
        l,t = self.pos
        w,h = self.size
        bgl.glEnable(bgl.GL_BLEND)
        self.drawing.line_width(1)
        bgl.glColor4f(0,0,0,0.1)
        bgl.glBegin(bgl.GL_LINE_STRIP)
        bgl.glVertex2f(l,t)
        bgl.glVertex2f(l,t-h)
        bgl.glVertex2f(l+w,t-h)
        bgl.glVertex2f(l+w,t)
        bgl.glVertex2f(l,t)
        bgl.glEnd()
        super()._draw()


class UI_Image(UI_Element):
    def __init__(self, image_data):
        super().__init__()
        self.height,self.width,self.depth = len(image_data),len(image_data[0]),len(image_data[0][0])
        assert self.depth == 4
        
        image_flat = [d for r in image_data for c in r for d in c]
        
        texbuffer = bgl.Buffer(bgl.GL_INT, [1])
        bgl.glGenTextures(1, texbuffer)
        self.texture_id = texbuffer.to_list()[0]
        del texbuffer
        
        bgl.glBindTexture(bgl.GL_TEXTURE_2D, self.texture_id)
        bgl.glTexEnvf(bgl.GL_TEXTURE_ENV, bgl.GL_TEXTURE_ENV_MODE, bgl.GL_MODULATE)
        bgl.glTexParameterf(bgl.GL_TEXTURE_2D, bgl.GL_TEXTURE_MAG_FILTER, bgl.GL_LINEAR)
        bgl.glTexParameterf(bgl.GL_TEXTURE_2D, bgl.GL_TEXTURE_MIN_FILTER, bgl.GL_LINEAR)
        # texbuffer = bgl.Buffer(bgl.GL_BYTE, [self.width,self.height,self.depth], image_data)
        texbuffer = bgl.Buffer(bgl.GL_BYTE, [self.width*self.height*self.depth], image_flat)
        bgl.glTexImage2D(bgl.GL_TEXTURE_2D, 0, bgl.GL_RGBA, self.width, self.height, 0, bgl.GL_RGBA, bgl.GL_UNSIGNED_BYTE, texbuffer)
        del texbuffer
        bgl.glBindTexture(bgl.GL_TEXTURE_2D, 0)
    
    def _get_width(self): return self.drawing.scale(self.width)
    def _get_height(self): return self.drawing.scale(self.height)
    
    def set_width(self, w): self.width = w
    def set_height(self, h): self.height = h
    def set_size(self, w, h): self.width,self.height = w,h
    
    def _draw(self):
        cx,cy = self.pos + self.size / 2
        w,h = self.drawing.scale(self.width),self.drawing.scale(self.height)
        l,t = cx-w/2, cy-h/2
        
        bgl.glColor4f(1,1,1,1)
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_TEXTURE_2D)
        bgl.glBindTexture(bgl.GL_TEXTURE_2D, self.texture_id)
        bgl.glBegin(bgl.GL_QUADS)
        bgl.glTexCoord2f(0,0)
        bgl.glVertex2f(l,t)
        bgl.glTexCoord2f(0,1)
        bgl.glVertex2f(l,t-h)
        bgl.glTexCoord2f(1,1)
        bgl.glVertex2f(l+w,t-h)
        bgl.glTexCoord2f(1,0)
        bgl.glVertex2f(l+w,t)
        bgl.glEnd()
        bgl.glBindTexture(bgl.GL_TEXTURE_2D, 0)
        


class UI_Graphic(UI_Element):
    def __init__(self, graphic=None):
        super().__init__()
        self._graphic = graphic
        self.width = 12
        self.height = 12
    
    def set_graphic(self, graphic): self._graphic = graphic
    
    def _get_width(self): return self.dpi_mult * self.width
    def _get_height(self): return self.dpi_mult * self.height
    
    def _draw(self):
        cx = self.pos.x + self.size.x / 2
        cy = self.pos.y - self.size.y / 2
        w,h = self.dpi_mult * self.width,self.dpi_mult * self.height
        l,t = cx-w/2, cy+h/2
        
        self.drawing.line_width(1.0)
        
        if self._graphic == 'box unchecked':
            bgl.glColor4f(1,1,1,1)
            bgl.glBegin(bgl.GL_LINE_STRIP)
            bgl.glVertex2f(l,t)
            bgl.glVertex2f(l,t-h)
            bgl.glVertex2f(l+w,t-h)
            bgl.glVertex2f(l+w,t)
            bgl.glVertex2f(l,t)
            bgl.glEnd()
        
        elif self._graphic == 'box checked':
            bgl.glColor4f(0.27,0.50,0.72,0.90)
            bgl.glBegin(bgl.GL_QUADS)
            bgl.glVertex2f(l,t)
            bgl.glVertex2f(l,t-h)
            bgl.glVertex2f(l+w,t-h)
            bgl.glVertex2f(l+w,t)
            bgl.glEnd()
            bgl.glColor4f(1,1,1,1)
            bgl.glBegin(bgl.GL_LINE_STRIP)
            bgl.glVertex2f(l,t)
            bgl.glVertex2f(l,t-h)
            bgl.glVertex2f(l+w,t-h)
            bgl.glVertex2f(l+w,t)
            bgl.glVertex2f(l,t)
            bgl.glEnd()
            bgl.glBegin(bgl.GL_LINE_STRIP)
            bgl.glVertex2f(l+2,cy)
            bgl.glVertex2f(cx,t-h+2)
            bgl.glVertex2f(l+w-2,t-2)
            bgl.glEnd()
        
        elif self._graphic == 'triangle right':
            bgl.glColor4f(1,1,1,1)
            bgl.glBegin(bgl.GL_TRIANGLES)
            bgl.glVertex2f(l+2,t-2)
            bgl.glVertex2f(l+2,t-h+2)
            bgl.glVertex2f(l+w-2,cy)
            bgl.glEnd()
        
        elif self._graphic == 'triangle down':
            bgl.glColor4f(1,1,1,1)
            bgl.glBegin(bgl.GL_TRIANGLES)
            bgl.glVertex2f(l+2,t-2)
            bgl.glVertex2f(cx,t-h+2)
            bgl.glVertex2f(l+w-2,t-2)
            bgl.glEnd()


class UI_Checkbox(UI_Container):
    '''
    [ ] Label
    [V] Label
    '''
    def __init__(self, label, fn_get_checked, fn_set_checked, options={}):
        spacing = options.get('spacing', 4)
        super().__init__(vertical=False)
        self.margin = 0
        self.chk = UI_Graphic()
        self.lbl = UI_Label(label)
        self.add(self.chk)
        self.add(UI_Spacer(width=spacing))
        self.add(self.lbl)
        self.fn_get_checked = fn_get_checked
        self.fn_set_checked = fn_set_checked
    
    def hover_ui(self, mouse):
        return self if super().hover_ui(mouse) else None
    
    def mouse_up(self, mouse): self.fn_set_checked(not self.fn_get_checked())
    
    def predraw(self):
        self.chk.set_graphic('box checked' if self.fn_get_checked() else 'box unchecked')


class UI_Checkbox2(UI_Container):
    '''
    Label
    Label  <- highlighted if checked
    '''
    def __init__(self, label, fn_get_checked, fn_set_checked, options={}):
        super().__init__()
        self.margin = 0
        self.add(UI_Label(label, align=0))
        self.fn_get_checked = fn_get_checked
        self.fn_set_checked = fn_set_checked
    
    def hover_ui(self, mouse):
        return self if super().hover_ui(mouse) else None
    def mouse_up(self, mouse): self.fn_set_checked(not self.fn_get_checked())
    
    def _draw(self):
        l,t = self.pos
        w,h = self.size
        
        self.drawing.line_width(1.0)
        bgl.glEnable(bgl.GL_BLEND)
        
        if self.fn_get_checked():
            bgl.glColor4f(0.27,0.50,0.72,0.90)
            bgl.glBegin(bgl.GL_QUADS)
            bgl.glVertex2f(l,t)
            bgl.glVertex2f(l,t-h)
            bgl.glVertex2f(l+w,t-h)
            bgl.glVertex2f(l+w,t)
            bgl.glEnd()
        else:
            bgl.glColor4f(0,0,0,0)
            bgl.glBegin(bgl.GL_QUADS)
            bgl.glVertex2f(l,t)
            bgl.glVertex2f(l,t-h)
            bgl.glVertex2f(l+w,t-h)
            bgl.glVertex2f(l+w,t)
            bgl.glEnd()
        
        bgl.glColor4f(0,0,0,0.1)
        bgl.glBegin(bgl.GL_LINE_STRIP)
        bgl.glVertex2f(l,t)
        bgl.glVertex2f(l,t-h)
        bgl.glVertex2f(l+w,t-h)
        bgl.glVertex2f(l+w,t)
        bgl.glVertex2f(l,t)
        bgl.glEnd()
        
        super()._draw()

class UI_BoolValue(UI_Checkbox):
    pass

class UI_IntValue(UI_Container):
    def __init__(self, label, fn_get_value, fn_set_value):
        super().__init__(vertical=False)
        # self.margin = 0
        self.lbl = UI_Label(label)
        self.val = UI_Label(fn_get_value())
        self.add(self.lbl)
        self.add(UI_Label(':'))
        self.add(UI_Spacer(width=4))
        self.add(self.val)
        self.fn_get_value = fn_get_value
        self.fn_set_value = fn_set_value
    
    def hover_ui(self, mouse):
        return self if super().hover_ui(mouse) else None
    
    def mouse_down(self, mouse):
        self.down_mouse = mouse
        self.down_val = self.fn_get_value()
        set_cursor('MOVE_X')
    
    def mouse_move(self, mouse):
        self.fn_set_value(self.down_val + int((mouse.x - self.down_mouse.x)/10))
    
    def predraw(self):
        self.val.set_label(self.fn_get_value())
    
    def _draw(self):
        l,t = self.pos
        w,h = self.size
        bgl.glEnable(bgl.GL_BLEND)
        self.drawing.line_width(1)
        bgl.glColor4f(0,0,0,0.1)
        bgl.glBegin(bgl.GL_LINE_STRIP)
        bgl.glVertex2f(l,t)
        bgl.glVertex2f(l,t-h)
        bgl.glVertex2f(l+w,t-h)
        bgl.glVertex2f(l+w,t)
        bgl.glVertex2f(l,t)
        bgl.glEnd()
        super()._draw()


class UI_HBFContainer(UI_Container):
    '''
    container with header, body, and footer
    '''
    def __init__(self, vertical=True):
        super().__init__()
        self.margin = 0
        self.header = UI_Container()
        self.body = UI_Container(vertical=vertical)
        self.footer = UI_Container()
        # self.header.margin = 0
        # self.body.margin = 0
        # self.footer.margin = 0
        super().add(self.header)
        super().add(self.body)
        super().add(self.footer)
    
    def hover_ui(self, mouse):
        if not super().hover_ui(mouse): return None
        ui = self.header.hover_ui(mouse)
        if ui: return ui
        ui = self.body.hover_ui(mouse)
        if ui: return ui
        ui = self.footer.hover_ui(mouse)
        if ui: return ui
        return self
    
    def _get_width(self): return max(c.get_width() for c in self.ui_items if c.ui_items)
    def _get_height(self): return sum(c.get_height() for c in self.ui_items if c.ui_items)
    
    def add(self, ui_item, header=False, footer=False):
        if header: self.header.add(ui_item)
        elif footer: self.footer.add(ui_item)
        else: self.body.add(ui_item)
        return ui_item


class UI_Collapsible(UI_Container):
    def __init__(self, title, collapsed=True, equal=False, vertical=True):
        super().__init__()
        self.margin = 0
        
        self.header = UI_Container(background=(0,0,0,0.2))
        self.body = UI_Container(vertical=vertical) if not equal else UI_EqualContainer(vertical=vertical)
        self.footer = UI_Container()
        
        self.header.margin = 0
        # self.body.margin = 0
        self.footer.margin = 0
        
        self.title = self.header.add(UI_Container(vertical=False))
        self.title.margin = 0
        self.title_arrow = self.title.add(UI_Graphic('triangle down'))
        self.title_label = self.title.add(UI_Label(title))
        # self.header.add(UI_Rule(color=(0,0,0,0.25)))
        
        self.footer.add(UI_Rule(color=(0,0,0,0.25)))
        
        self.collapsed = collapsed
        
        self.versions = {
            False: [self.header, self.body, self.footer],
            True: [self.header]
        }
        self.graphics = {
            False: 'triangle down',
            True: 'triangle right',
        }
        
        super().add(self.header)
    
    def expand(self): self.collapsed = False
    def collapse(self): self.collapsed = True
    
    def predraw(self):
        #self.title.set_bgcolor(self.bgcolors[self.collapsed])
        self.title_arrow.set_graphic(self.graphics[self.collapsed])
        self.ui_items = self.versions[self.collapsed]
    
    def _get_width(self): return max(c.get_width() for c in self.ui_items if c.ui_items)
    def _get_height(self): return sum(c.get_height() for c in self.ui_items if c.ui_items)
    
    def add(self, ui_item, header=False):
        if header: self.header.add(ui_item)
        else: self.body.add(ui_item)
        return ui_item
    
    def hover_ui(self, mouse):
        if not super().hover_ui(mouse): return None
        if self.collapsed: return self
        return self.body.hover_ui(mouse) or self
    
    def mouse_up(self, mouse):
        self.collapsed = not self.collapsed


class UI_Padding(UI_Element):
    def __init__(self, ui_item=None, padding=5):
        super().__init__()
        self.margin = 0
        self.padding = padding
        self.ui_item = ui_item
    
    def set_ui_item(self, ui_item): self.ui_item = ui_item
    
    def hover_ui(self, mouse):
        if not super().hover_ui(mouse): return None
        ui = None if not self.ui_item else self.ui_item.hover_ui(mouse)
        return ui or self
    
    def _get_width(self):
        return self.dpi_mult * (self.padding*2) + (0 if not self.ui_item else self.ui_item.get_width())
    def _get_height(self):
        return self.dpi_mult * (self.padding*2) + (0 if not self.ui_item else self.ui_item.get_height())
    
    def _draw(self):
        if not self.ui_item: return
        p = self.padding
        l,t = self.pos
        w,h = self.size
        self.ui_item.draw(l+p,t-p,w-p*2,h-p*2)
    


class UI_Window(UI_Padding):
    screen_margin = 5
    
    def __init__(self, title, options):
        pos = options.get('pos', None)
        sticky = options.get('sticky', None)
        vertical = options.get('vertical', True)
        padding = options.get('padding', 0)
        visible = options.get('visible', True)
        movable = options.get('movable', True)
        
        super().__init__(padding=padding)
        self.margin = 0
        
        self.visible = visible
        self.movable = movable
        
        self.drawing.text_size(12)
        self.hbf = UI_HBFContainer(vertical=vertical)
        self.hbf.header.margin = 1
        self.hbf.header.background = (0,0,0,0.2)
        self.hbf_title = UI_Label(title, align=0, color=(1,1,1,0.5))
        self.hbf_title.margin = 1
        self.hbf_title_rule = UI_Rule(color=(0,0,0,0.1))
        self.hbf.add(self.hbf_title, header=True)
        self.hbf.add(self.hbf_title_rule, header=True)
        self.set_ui_item(self.hbf)
        
        self.update_pos(pos=pos or Point2D((0,0)), sticky=sticky)
        self.ui_grab = [self, self.hbf_title, self.hbf_title_rule]
        
        self.FSM = {}
        self.FSM['main'] = self.modal_main
        self.FSM['move'] = self.modal_move
        self.FSM['down'] = self.modal_down
        self.state = 'main'
        
        self.win_width,self.win_height = 1,1
    
    def show(self): self.visible = True
    def hide(self): self.visible = False
    
    def add(self, *args, **kwargs): return self.hbf.add(*args, **kwargs)
    
    def update_pos(self, pos:Point2D=None, sticky=None):
        m = self.screen_margin
        sw,sh = self.context.region.width,self.context.region.height
        cw,ch = round(sw/2),round(sh/2)
        w,h = self.get_width(),self.get_height()
        
        if sticky is not None:
            self.sticky = sticky
            self.pos = pos or self.pos
        elif pos:
            self.pos = pos
            self.sticky = 0
            l,t = self.pos
            stick_top,stick_bot = t >= sh - m, t <= m + h
            stick_left,stick_right = l <= m, l >= sw - m - w
            if stick_top:
                if stick_left: self.sticky = 7
                if stick_right: self.sticky = 9
            elif stick_bot:
                if stick_left: self.sticky = 1
                if stick_right: self.sticky = 3
        
        positions = {
            7: (0, sh), 8: (cw, sh), 9: (sw, sh),
            4: (0, ch), 5: (cw, ch), 6: (sw, ch),
            1: (0, 0),  2: (cw, 0),  3: (sw, 0),
            0: self.pos,
        }
        l,t = positions[self.sticky]
        l,t = max(m, min(sw-m-w,l)),max(m+h, min(sh-m,t))     # clamp position so window is always seen
        
        self.pos = Point2D((l,t))
        self.size = Vec2D((w,h))
    
    def draw_postpixel(self):
        if not self.visible: return
        
        bgl.glEnable(bgl.GL_BLEND)
        self.drawing.text_size(12)
        
        self.update_pos()
        
        l,t = self.pos
        w,h = self.size
        
        # draw background
        bgl.glColor4f(0,0,0,0.25)
        bgl.glBegin(bgl.GL_QUADS)
        bgl.glVertex2f(l,t)
        bgl.glVertex2f(l,t-h)
        bgl.glVertex2f(l+w,t-h)
        bgl.glVertex2f(l+w,t)
        bgl.glEnd()
        
        self.drawing.line_width(1.0)
        bgl.glColor4f(0,0,0,0.5)
        bgl.glBegin(bgl.GL_LINE_STRIP)
        bgl.glVertex2f(l,t)
        bgl.glVertex2f(l,t-h)
        bgl.glVertex2f(l+w,t-h)
        bgl.glVertex2f(l+w,t)
        bgl.glVertex2f(l,t)
        bgl.glEnd()
        
        self.draw(l, t, w, h)
    
    def modal(self, context, event):
        if context.region:
            self.win_width,self.win_height = context.region.width,context.region.height
        self.mouse = Point2D((float(event.mouse_region_x), float(event.mouse_region_y)))
        self.context = context
        self.event = event
        
        if not self.visible: return
        
        nstate = self.FSM[self.state]()
        self.state = nstate or self.state
        
        return {'hover'} if self.hover_ui(self.mouse) or self.state != 'main' else {}
    
    def modal_main(self):
        ui_hover = self.hover_ui(self.mouse)
        if not ui_hover: return
        set_cursor(ui_hover.mouse_cursor()) #'DEFAULT')
        if self.event.type == 'LEFTMOUSE' and self.event.value == 'PRESS':
            if self.movable and ui_hover in self.ui_grab:
                self.mouse_down = self.mouse
                self.mouse_prev = self.mouse
                self.pos_prev = self.pos
                return 'move'
            self.ui_down = ui_hover
            self.ui_down.mouse_down(self.mouse)
            return 'down'
    
    def modal_move(self):
        set_cursor('HAND')
        if self.event.type == 'LEFTMOUSE' and self.event.value == 'RELEASE':
            return 'main'
        diff = self.mouse - self.mouse_down
        self.update_pos(pos=self.pos_prev + diff)
        self.mouse_prev = self.mouse
    
    def modal_down(self):
        if self.event.type == 'LEFTMOUSE' and self.event.value == 'RELEASE':
            self.ui_down.mouse_up(self.mouse)
            return 'main'
        self.ui_down.mouse_move(self.mouse)


class UI_WindowManager:
    def __init__(self):
        self.windows = []
        self.active = None
    
    def create_window(self, title, options):
        win = UI_Window(title, options)
        self.windows.append(win)
        return win
    
    def draw_postpixel(self):
        for win in self.windows:
            win.draw_postpixel()
    
    def modal(self, context, event):
        if self.active:
            ret = self.active.modal(context, event)
            if not ret: self.active = None
        else:
            for win in reversed(self.windows):
                ret = win.modal(context, event)
                if ret:
                    self.active = win
                    break
        return ret



