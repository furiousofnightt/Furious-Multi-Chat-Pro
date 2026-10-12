import base64
from PyQt6.QtGui import QImage, QPainter, QPainterPath, QColor, QPen, QPixmap
from PyQt6.QtCore import Qt, QByteArray, QBuffer, QIODevice, QRectF


def make_circular_image(image_bytes, size=38, border_color=None, border_width=1.5):
    """
    Recorta qualquer imagem em formato perfeitamente circular usando QImage (100% thread-safe).
    Funciona em qualquer thread (GUI ou background).
    """
    if not image_bytes or not isinstance(image_bytes, (bytes, bytearray)):
        return None

    img = QImage()
    if not img.loadFromData(image_bytes):
        return None

    if img.isNull() or img.width() <= 0 or img.height() <= 0:
        return None

    scaled = img.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)

    target = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    target.fill(Qt.GlobalColor.transparent)

    painter = QPainter(target)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    path = QPainterPath()
    has_border = bool(border_color and border_width > 0)
    offset = (border_width / 2.0) if has_border else 0.0
    diameter = float(size - (border_width if has_border else 0.0))

    rect = QRectF(offset, offset, diameter, diameter)
    path.addEllipse(rect)
    painter.setClipPath(path)

    x = (size - scaled.width()) // 2
    y = (size - scaled.height()) // 2
    painter.drawImage(x, y, scaled)

    if has_border:
        painter.setClipping(False)
        pen = QPen(QColor(border_color))
        pen.setWidthF(border_width)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(rect)

    painter.end()
    return target


def make_circular_base64_png(image_bytes, size=22, border_color="rgba(255, 255, 255, 120)", border_width=1.0):
    """
    Gera Base64 PNG circular para uso em tags HTML <img> do Qt sem cantos quadrados.
    Thread-safe para uso em loops assíncronos.
    """
    try:
        circ_img = make_circular_image(image_bytes, size=size, border_color=border_color, border_width=border_width)
        if not circ_img or circ_img.isNull():
            return None

        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        circ_img.save(buffer, "PNG")
        buffer.close()

        return base64.b64encode(byte_array.data()).decode('utf-8')
    except Exception as e:
        print(f"⚠️ Erro ao gerar avatar circular base64: {e}")
        return None


def make_circular_pixmap_from_bytes(image_bytes, size=38, border_color="rgba(0, 230, 230, 180)", border_width=1.5):
    """
    Retorna um QPixmap perfeitamente circular a partir dos bytes da imagem.
    """
    try:
        circ_img = make_circular_image(image_bytes, size=size, border_color=border_color, border_width=border_width)
        if circ_img and not circ_img.isNull():
            return QPixmap.fromImage(circ_img)
    except Exception as e:
        print(f"⚠️ Erro ao gerar pixmap circular: {e}")
    return None
