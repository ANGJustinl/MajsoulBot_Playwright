class MyClick:
    def __init__(self, page=None):
        """
        Initialize click handler with optional Playwright page
        Args:
            page: Playwright page object
        """
        self.page = page
        self.top_left_corner = (0, 0)

    def set_top_left_corner(self, box):
        """Set the top-left corner coordinates of the game window"""
        self.top_left_corner = (box[0], box[1])

    def click(self, box, click=True, center=True) -> None:
        """
        Move to and optionally click at the specified coordinates
        Args:
            box: Tuple of (left, top, right, bottom) coordinates
            click: Whether to perform click action
            center: Whether to click at center of box (True) or top-left corner (False)
        """
        if center:
            x = (box[0] + box[2]) // 2 + self.top_left_corner[0]
            y = (box[1] + box[3]) // 2 + self.top_left_corner[1]
        else:  # click top-left corner
            x = box[0] + self.top_left_corner[0]
            y = box[1] + self.top_left_corner[1]

        if self.page:
            self.page.mouse.move(x, y)
            if click:
                print('click x = %d, y = %d' % (x, y))
                self.page.mouse.click(x, y)
        else:
            print("Warning: No Playwright page available for clicking")
