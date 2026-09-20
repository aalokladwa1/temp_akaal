import cv2
import numpy as np

def img_to_svg(img_path, out_svg, epsilon=1.0):
    img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
    alpha = img[:, :, 3]
    mask = ((alpha > 50) & (img[:, :, 0] < 128)).astype(np.uint8) * 255
    h, w = mask.shape
    
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_KCOS)
    
    path_d = []
    for i, c in enumerate(contours):
        area = cv2.contourArea(c)
        if area < 10: continue
        approx = cv2.approxPolyDP(c, epsilon, True)
        if len(approx) < 3: continue
        d = f'M {approx[0][0][0]} {approx[0][0][1]}'
        for pt in approx[1:]:
            d += f' L {pt[0][0]} {pt[0][1]}'
        d += ' Z'
        path_d.append(d)
        
    full_d = ' '.join(path_d)
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" fill="currentColor">
  <path fill-rule="evenodd" d="{full_d}" />
</svg>'''
    with open(out_svg, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print(f'Wrote {out_svg}: viewBox 0 0 {w} {h}, {len(contours)} contours')

img_to_svg('artifacts/mark_hires.png', 'artifacts/devkros-logo.svg', epsilon=1.0)
img_to_svg('artifacts/wordmark_hires.png', 'artifacts/devkros-wordmark.svg', epsilon=0.6)
