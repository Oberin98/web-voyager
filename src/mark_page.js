const customCSS = `
    ::-webkit-scrollbar {
        width: 10px;
    }
    ::-webkit-scrollbar-track {
        background: #27272a;
    }
    ::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 0.375rem;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
`;

const styleTag = document.createElement("style");
styleTag.textContent = customCSS;
document.head.append(styleTag);

let labels = [];

/**
 * Interactable elements
 */
const selectors = [
  "a",
  "button",
  "input",
  "textarea",
  "select",
  "[role='button']",
  "[role='link']",
  "[role='checkbox']",
  "[role='radio']",
  "[role='tab']",
  "[role='menuitem']",
  "[onclick]",
  "[tabindex='0']",
];

/**
 * Check if an element is visible on the page and in the viewport
 */
function isElementVisible(element) {
  // Check if the element is visible by styles
  const style = window.getComputedStyle(element);

  const isVisibleByStyle =
    style.display !== "none" &&
    style.visibility !== "hidden" &&
    style.opacity !== "0" &&
    element.offsetWidth > 0 &&
    element.offsetHeight > 0;

  // Check if the element is in the viewport
  const rect = element.getBoundingClientRect();

  const vw = Math.max(
    document.documentElement.clientWidth || 0,
    window.innerWidth || 0
  );

  const vh = Math.max(
    document.documentElement.clientHeight || 0,
    window.innerHeight || 0
  );

  const isInViewport =
    rect.top < vh && rect.left < vw && rect.bottom > 0 && rect.right > 0;

  return isVisibleByStyle && isInViewport;
}

/**
 * Generate a random color
 */
function getRandomColor() {
  var letters = "0123456789ABCDEF";
  var color = "#";
  for (var i = 0; i < 6; i++) {
    color += letters[Math.floor(Math.random() * 16)];
  }
  return color;
}

/**
 * Remove all the floating mark elements from the page
 */
function removeStyleMarks() {
  for (const label of labels) {
    document.body.removeChild(label);
  }

  labels = [];
}

/**
 * Remove all the data-interactive-index attributes from the page
 */
function removeAttributeMarks() {
  const elements = document.querySelectorAll("[data-interactive-index]");

  for (let i = 0; i < elements.length; i++) {
    elements[i].removeAttribute("data-interactive-index");
  }
}

/**
 * Mark interactable elements on the page
 */
function markPage() {
  removeStyleMarks();
  removeAttributeMarks();

  let items = [...document.querySelectorAll(selectors.join(", "))].reduce(
    (acc, element) => {
      if (isElementVisible(element)) {
        const rects = element.getBoundingClientRect();
        const ariaLabel = element.getAttribute("aria-label") || "";
        const elementType = element.tagName.toLowerCase();
        const textualContent = element.textContent
          .trim()
          .replace(/\s{2,}/g, " ");

        acc.push({
          element,
          rects,
          text: textualContent,
          type: elementType,
          ariaLabel: ariaLabel,
        });
      }

      return acc;
    },
    []
  );

  //Only keep inner clickable items
  items = items.filter(
    (x) => !items.some((y) => x.element.contains(y.element) && !(x == y))
  );

  items.forEach((item, index) => {
    // Make all links open in the same tab because agent can make screenshot only of one page
    if (item.type === "a") {
      item.element.setAttribute("target", "_self");
    }

    // Mark element with custom data attribute for interaction
    item.element.setAttribute("data-interactive-index", index);
  });

  // Add floating border on top of these elements that will always be visible
  items.forEach((item, index) => {
    const elementColor = getRandomColor();

    const markElement = document.createElement("div");

    Object.assign(markElement.style, {
      outline: `2px dashed ${elementColor}`,
      position: "fixed",
      left: `${item.rects.left}px`,
      top: `${item.rects.top}px`,
      width: `${item.rects.width}px`,
      height: `${item.rects.height}px`,
      pointerEvents: "none",
      boxSizing: "border-box",
      zIndex: 2147483647,
    });

    // Add floating label at the corner
    const markLabel = document.createElement("div");

    markLabel.textContent = index;

    Object.assign(markLabel.style, {
      position: "absolute",
      top: "-19px",
      left: "0px",
      background: elementColor,
      color: "white",
      padding: "2px 4px",
      fontSize: "12px",
      borderRadius: "2px",
    });

    markElement.appendChild(markLabel);
    document.body.appendChild(markElement);
    labels.push(markElement);
  });

  const coordinates = items.flatMap((item) => {
    return {
      x: item.rects.x + item.rects.width / 2,
      y: item.rects.y + item.rects.height / 2,
      type: item.type,
      text: item.text,
      ariaLabel: item.ariaLabel,
    };
  });

  return coordinates;
}
