from dataclasses import dataclass
from enum import Enum
from typing import Optional
import copy


class ActionType(Enum):
    """
    Types of UI interactions
    """
    CLICK = "click"
    EDIT = "edit"
    SCROLL = "scroll"
    # ...add more as we go along

class UIElementType(Enum):
    """
    Types of UI elements
    """
    BUTTON = "button"
    INPUT = "input"
    LINK = "link"
    # ...add more as we go along

@dataclass
class UIElement:
    """
    Represents a targetable UI element.
    When crawling (via str()), stable attributes (id, name) are prioritized over volatile ones (class).
    """
    element_type: UIElementType # type of the element, needs to be considered when performing actions

    # selectors ordered by stability (priority)
    id: Optional[str] = None  # e.g. id="username"
    name: Optional[str] = None # e.g. name="username"

    # fallbacks
    class_name: Optional[str] = None # e.g. class="radius"
    text_content: Optional[str] = None # e.g. "Log in"

    def __str__(self):
        """
        String representation for the UIElement, prioritizing uniqueness and stability.
        Note that these are not CSS selectors, but meant for human readability.
        (code_gen.py is responsible for generating actual selectors)
        """
        if self.id:
            return f"{self.element_type.value}[id='{self.id}']"
        elif self.name:
            return f"{self.element_type.value}[name='{self.name}']"
        elif self.class_name:
            return f"{self.element_type.value}[class='{self.class_name}']"
        elif self.text_content:
            return f"{self.element_type.value}[text='{self.text_content[:15]}...']"
        return f"{self.element_type.value}[unknown selector]"


    def __deepcopy__(self):
        return UIElement(
            element_type=self.element_type,
            id=self.id,
            name=self.name,
            class_name=self.class_name,
            text_content=self.text_content
        )

@dataclass
class Action:
    """
    Represents a single UI action
    """
    action_type: ActionType
    target: Optional[UIElement] = None # optional, as action can e.g. just be a scroll
    data: Optional[str] = None # optional, e.g. for EDIT actions

    def __str__(self):
        if self.action_type == ActionType.EDIT:
            return f"Edit {self.target} with '{self.data}'"
        elif self.target:
            return f"{self.action_type.value.upper()} {self.target}"
        else:
            return f"{self.action_type.value.upper()}"

    def __deepcopy__(self):
        return Action(
            action_type=self.action_type,
            target=copy.deepcopy(self.target),
            data=self.data
        )

class Chromosome:
    """
    Sequence of actions that can be executed on a UI
    """

    def __init__(self, actions=None):
        if actions is None:
            actions = []
        self.actions = actions
        self.fitness = None
        # ...potentially more attributes for tracking performance metrics

    def __len__(self):
        return len(self.actions)

    def __getitem__(self, index):
        return self.actions[index]

    def __str__(self):
        fitness_str = f"{self.fitness:.3f}" if self.fitness is not None else "??"
        return f"Chromosome(fitness={fitness_str}, length={len(self)}])"

    def __deepcopy__(self):
        return Chromosome(
            actions=[copy.deepcopy(action) for action in self.actions]
        )

    def add_action(self, action: Action):
        self.actions.append(action)




