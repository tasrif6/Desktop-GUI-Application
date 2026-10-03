from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPainterPath, QFont
from PySide6.QtCore import Qt, QRectF, QPointF

def create_badge_icon(icon_type: str, bg_color: str, size: int = 40) -> QIcon:
    """Creates a polished circular badge with a solid color and crisp white vector icon inside."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    # Draw circular background
    p.setBrush(QBrush(QColor(bg_color)))
    p.setPen(Qt.NoPen)
    p.drawEllipse(1, 1, size - 2, size - 2)

    s = size
    pen = QPen(QColor("#ffffff"))
    pen.setWidthF(1.8)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    if icon_type == "user" or icon_type == "eligible":
        # White user icon
        p.setBrush(QBrush(QColor("#ffffff")))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(s * 0.5, s * 0.36), s * 0.16, s * 0.16)
        path = QPainterPath()
        path.arcMoveTo(QRectF(s * 0.22, s * 0.54, s * 0.56, s * 0.40), 0)
        path.arcTo(QRectF(s * 0.22, s * 0.54, s * 0.56, s * 0.40), 0, 180)
        path.closeSubpath()
        p.drawPath(path)

    elif icon_type == "ban" or icon_type == "excluded":
        # Slashed circle
        p.setPen(QPen(QColor("#ffffff"), 2.4))
        r = s * 0.28
        p.drawEllipse(QPointF(s * 0.5, s * 0.5), r, r)
        diag = r * 0.707
        p.drawLine(QPointF(s * 0.5 - diag, s * 0.5 - diag), QPointF(s * 0.5 + diag, s * 0.5 + diag))

    elif icon_type == "users" or icon_type == "grouped":
        # Multiple users
        p.setBrush(QBrush(QColor("#ffffff")))
        p.setPen(Qt.NoPen)
        # Left user
        p.drawEllipse(QPointF(s * 0.38, s * 0.36), s * 0.13, s * 0.13)
        b1 = QPainterPath()
        b1.arcMoveTo(QRectF(s * 0.16, s * 0.52, s * 0.44, s * 0.36), 0)
        b1.arcTo(QRectF(s * 0.16, s * 0.52, s * 0.44, s * 0.36), 0, 180)
        b1.closeSubpath()
        p.drawPath(b1)
        # Right user
        p.drawEllipse(QPointF(s * 0.64, s * 0.40), s * 0.11, s * 0.11)
        b2 = QPainterPath()
        b2.arcMoveTo(QRectF(s * 0.46, s * 0.55, s * 0.36, s * 0.32), 0)
        b2.arcTo(QRectF(s * 0.46, s * 0.55, s * 0.36, s * 0.32), 0, 180)
        b2.closeSubpath()
        p.drawPath(b2)

    elif icon_type == "gift" or icon_type == "rebate":
        # Gift box
        p.setPen(QPen(QColor("#ffffff"), 1.8))
        p.drawRoundedRect(QRectF(s * 0.24, s * 0.42, s * 0.52, s * 0.42), 2, 2)
        p.drawRoundedRect(QRectF(s * 0.20, s * 0.32, s * 0.60, s * 0.12), 2, 2)
        p.drawLine(QPointF(s * 0.50, s * 0.32), QPointF(s * 0.50, s * 0.84))
        # Bow loops
        p.drawEllipse(QPointF(s * 0.43, s * 0.26), s * 0.08, s * 0.06)
        p.drawEllipse(QPointF(s * 0.57, s * 0.26), s * 0.08, s * 0.06)

    elif icon_type == "gear":
        # White cog gear
        p.setPen(QPen(QColor("#ffffff"), 2))
        p.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.25, s * 0.25)
        p.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.10, s * 0.10)
        for angle in (0, 45, 90, 135):
            p.save()
            p.translate(s * 0.5, s * 0.5)
            p.rotate(angle)
            p.drawLine(QPointF(0, -s * 0.35), QPointF(0, s * 0.35))
            p.restore()

    elif icon_type == "document" or icon_type == "checklist":
        # Document icon
        p.setPen(QPen(QColor("#ffffff"), 1.8))
        rect = QRectF(s * 0.25, s * 0.20, s * 0.50, s * 0.60)
        p.drawRoundedRect(rect, 2, 2)
        p.drawLine(QPointF(s * 0.35, s * 0.38), QPointF(s * 0.65, s * 0.38))
        p.drawLine(QPointF(s * 0.35, s * 0.50), QPointF(s * 0.65, s * 0.50))
        p.drawLine(QPointF(s * 0.35, s * 0.62), QPointF(s * 0.55, s * 0.62))

    elif icon_type == "info":
        p.setPen(QPen(QColor("#ffffff"), 2))
        p.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.36, s * 0.36)
        p.setBrush(QBrush(QColor("#ffffff")))
        p.drawEllipse(QPointF(s * 0.5, s * 0.34), 1.8, 1.8)
        p.drawLine(QPointF(s * 0.5, s * 0.46), QPointF(s * 0.5, s * 0.68))

    elif icon_type == "bolt":
        path = QPainterPath()
        path.moveTo(s * 0.54, s * 0.16)
        path.lineTo(s * 0.30, s * 0.50)
        path.lineTo(s * 0.50, s * 0.50)
        path.lineTo(s * 0.46, s * 0.84)
        path.lineTo(s * 0.70, s * 0.44)
        path.lineTo(s * 0.50, s * 0.44)
        path.closeSubpath()
        p.setBrush(QBrush(QColor("#ffffff")))
        p.setPen(Qt.NoPen)
        p.drawPath(path)

    p.end()
    return QIcon(pix)


def get_vector_icon(name: str, color: str = "#ffffff", size: int = 24) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(1.8)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    s = size
    pad = s * 0.15

    if name == "app_logo":
        # Multi-bar analytics chart icon
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#38bdf8")))
        p.drawRoundedRect(QRectF(s * 0.12, s * 0.52, s * 0.20, s * 0.36), 2, 2)
        p.setBrush(QBrush(QColor("#60a5fa")))
        p.drawRoundedRect(QRectF(s * 0.40, s * 0.32, s * 0.20, s * 0.56), 2, 2)
        p.setBrush(QBrush(QColor("#818cf8")))
        p.drawRoundedRect(QRectF(s * 0.68, s * 0.14, s * 0.20, s * 0.74), 2, 2)

    elif name == "dashboard":
        w = s * 0.3
        p.drawRoundedRect(QRectF(pad, pad, w, w), 2, 2)
        p.drawRoundedRect(QRectF(s - pad - w, pad, w, w), 2, 2)
        p.drawRoundedRect(QRectF(pad, s - pad - w, w, w), 2, 2)
        p.drawRoundedRect(QRectF(s - pad - w, s - pad - w, w, w), 2, 2)

    elif name == "stock_data" or name == "database" or name == "party_lifting":
        cx, cy, w, h = s * 0.5, s * 0.28, s * 0.65, s * 0.22
        p.drawEllipse(QPointF(cx, cy), w / 2, h / 2)
        p.drawLine(QPointF(cx - w / 2, cy), QPointF(cx - w / 2, cy + s * 0.44))
        p.drawLine(QPointF(cx + w / 2, cy), QPointF(cx + w / 2, cy + s * 0.44))
        path = QPainterPath()
        path.arcMoveTo(QRectF(cx - w / 2, cy + s * 0.22 - h / 2, w, h), 180)
        path.arcTo(QRectF(cx - w / 2, cy + s * 0.22 - h / 2, w, h), 180, 180)
        p.drawPath(path)
        path2 = QPainterPath()
        path2.arcMoveTo(QRectF(cx - w / 2, cy + s * 0.44 - h / 2, w, h), 180)
        path2.arcTo(QRectF(cx - w / 2, cy + s * 0.44 - h / 2, w, h), 180, 180)
        p.drawPath(path2)

    elif name == "party_info" or name == "user" or name == "party_receivable":
        head_r = s * 0.18
        p.drawEllipse(QPointF(s * 0.5, s * 0.35), head_r, head_r)
        body = QPainterPath()
        body.arcMoveTo(QRectF(s * 0.2, s * 0.55, s * 0.6, s * 0.45), 0)
        body.arcTo(QRectF(s * 0.2, s * 0.55, s * 0.6, s * 0.45), 0, 180)
        p.drawPath(body)

    elif name == "excluded" or name == "ban":
        r = s * 0.34
        p.drawEllipse(QPointF(s * 0.5, s * 0.5), r, r)
        diag = r * 0.707
        p.drawLine(QPointF(s * 0.5 - diag, s * 0.5 - diag), QPointF(s * 0.5 + diag, s * 0.5 + diag))

    elif name == "rebate" or name == "receipt":
        rect = QRectF(s * 0.25, s * 0.16, s * 0.5, s * 0.68)
        p.drawRoundedRect(rect, 3, 3)
        p.drawLine(QPointF(s * 0.35, s * 0.34), QPointF(s * 0.65, s * 0.34))
        p.drawLine(QPointF(s * 0.35, s * 0.48), QPointF(s * 0.65, s * 0.48))
        p.drawLine(QPointF(s * 0.35, s * 0.62), QPointF(s * 0.52, s * 0.62))

    elif name == "grouped_parties" or name == "users":
        p.drawEllipse(QPointF(s * 0.38, s * 0.34), s * 0.14, s * 0.14)
        b1 = QPainterPath()
        b1.arcMoveTo(QRectF(s * 0.16, s * 0.52, s * 0.44, s * 0.36), 0)
        b1.arcTo(QRectF(s * 0.16, s * 0.52, s * 0.44, s * 0.36), 0, 180)
        p.drawPath(b1)

        p.drawEllipse(QPointF(s * 0.68, s * 0.38), s * 0.12, s * 0.12)
        b2 = QPainterPath()
        b2.arcMoveTo(QRectF(s * 0.48, s * 0.56, s * 0.40, s * 0.32), 0)
        b2.arcTo(QRectF(s * 0.48, s * 0.56, s * 0.40, s * 0.32), 0, 180)
        p.drawPath(b2)

    elif name == "results" or name == "report":
        rect = QRectF(s * 0.22, s * 0.15, s * 0.56, s * 0.7)
        p.drawRoundedRect(rect, 3, 3)
        p.drawLine(QPointF(s * 0.34, s * 0.70), QPointF(s * 0.34, s * 0.54))
        p.drawLine(QPointF(s * 0.46, s * 0.70), QPointF(s * 0.46, s * 0.42))
        p.drawLine(QPointF(s * 0.58, s * 0.70), QPointF(s * 0.58, s * 0.32))

    elif name == "logs" or name == "terminal":
        rect = QRectF(s * 0.22, s * 0.18, s * 0.56, s * 0.64)
        p.drawRoundedRect(rect, 3, 3)
        p.drawLine(QPointF(s * 0.32, s * 0.34), QPointF(s * 0.40, s * 0.34))
        p.drawLine(QPointF(s * 0.46, s * 0.34), QPointF(s * 0.68, s * 0.34))
        p.drawLine(QPointF(s * 0.32, s * 0.50), QPointF(s * 0.40, s * 0.50))
        p.drawLine(QPointF(s * 0.46, s * 0.50), QPointF(s * 0.68, s * 0.50))
        p.drawLine(QPointF(s * 0.32, s * 0.66), QPointF(s * 0.40, s * 0.66))
        p.drawLine(QPointF(s * 0.46, s * 0.66), QPointF(s * 0.68, s * 0.66))

    elif name == "about" or name == "info":
        p.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.35, s * 0.35)
        p.setBrush(QBrush(QColor(color)))
        p.drawEllipse(QPointF(s * 0.5, s * 0.34), 1.5, 1.5)
        p.drawLine(QPointF(s * 0.5, s * 0.46), QPointF(s * 0.5, s * 0.68))

    elif name == "search":
        r = s * 0.25
        p.drawEllipse(QPointF(s * 0.42, s * 0.42), r, r)
        p.drawLine(QPointF(s * 0.60, s * 0.60), QPointF(s * 0.82, s * 0.82))

    elif name == "play":
        path = QPainterPath()
        path.moveTo(s * 0.36, s * 0.24)
        path.lineTo(s * 0.74, s * 0.50)
        path.lineTo(s * 0.36, s * 0.76)
        path.closeSubpath()
        p.setBrush(QBrush(QColor(color)))
        p.setPen(Qt.NoPen)
        p.drawPath(path)

    elif name == "gear" or name == "settings":
        p.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.25, s * 0.25)
        p.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.10, s * 0.10)
        for angle in (0, 45, 90, 135):
            p.save()
            p.translate(s * 0.5, s * 0.5)
            p.rotate(angle)
            p.drawLine(QPointF(0, -s * 0.35), QPointF(0, s * 0.35))
            p.restore()

    elif name == "export" or name == "excel":
        rect = QRectF(s * 0.20, s * 0.20, s * 0.60, s * 0.60)
        p.drawRoundedRect(rect, 3, 3)
        p.drawLine(QPointF(s * 0.50, s * 0.34), QPointF(s * 0.50, s * 0.66))
        p.drawLine(QPointF(s * 0.34, s * 0.50), QPointF(s * 0.66, s * 0.50))

    elif name == "save":
        # Floppy disk icon
        rect = QRectF(s * 0.20, s * 0.20, s * 0.60, s * 0.60)
        p.drawRoundedRect(rect, 2, 2)
        p.drawRect(QRectF(s * 0.32, s * 0.20, s * 0.36, s * 0.25))
        p.drawRect(QRectF(s * 0.28, s * 0.55, s * 0.44, s * 0.25))

    elif name == "refresh" or name == "reset":
        rect = QRectF(s * 0.20, s * 0.20, s * 0.60, s * 0.60)
        path = QPainterPath()
        path.arcMoveTo(rect, 45)
        path.arcTo(rect, 45, 270)
        p.drawPath(path)
        p.drawLine(QPointF(s * 0.62, s * 0.16), QPointF(s * 0.64, s * 0.32))
        p.drawLine(QPointF(s * 0.64, s * 0.32), QPointF(s * 0.48, s * 0.30))

    elif name == "close" or name == "cancel":
        p.drawLine(QPointF(s * 0.28, s * 0.28), QPointF(s * 0.72, s * 0.72))
        p.drawLine(QPointF(s * 0.72, s * 0.28), QPointF(s * 0.28, s * 0.72))

    elif name == "minimize":
        p.drawLine(QPointF(s * 0.25, s * 0.62), QPointF(s * 0.75, s * 0.62))

    elif name == "maximize":
        p.drawRect(QRectF(s * 0.25, s * 0.25, s * 0.50, s * 0.50))

    else:
        p.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.3, s * 0.3)

    p.end()
    return QIcon(pix)
