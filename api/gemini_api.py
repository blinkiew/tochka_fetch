import base64

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError


load_dotenv()


class GeminiResponseError(ValueError):
    """Raised when Gemini does not return a valid structured schedule match."""


class ScheduleMatch(BaseModel):
    detected_grades: list[str] = Field(
        ...,
        description="Grades identified across images (e.g., ['5AT', '10 AT', '11'])"
    )
    reasoning: str = Field(
        ...,
        description="Explanation of why this image index was chosen"
    )
    target_image_index: int = Field(
        ...,
        description="0-based index of the image containing the schedule for 10th-11th grade"
    )
    confidence: float = Field(
        ...,
        description="Confidence score between 0.0 and 1.0"
    )


class GeminiAPI:
    def __init__(self):
        self.client = genai.Client()

    @staticmethod
    def _detect_mime_type(image_bytes: bytes) -> str:
        if image_bytes.startswith(b'\xff\xd8\xff'):
            return "image/jpeg"
        if image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            return "image/png"
        if image_bytes.startswith(b'RIFF') and image_bytes[8:12] == b'WEBP':
            return "image/webp"
        return "image/jpeg"

    def find_target_schedule(self, images: list[bytes]) -> ScheduleMatch:
        if not images:
            raise ValueError("At least one image is required.")

        contents = [
            "You are provided with images containing class schedules. "
            "Identify which image (by its 0-based index corresponding to the order provided below) "
            "contains the schedule for 10th and 11th grade students "
            "(e.g., columns labeled '10 AT', '10 БТ', '11', '10А', '11B', etc.)."
        ]

        for image_bytes in images:
            mime_type = self._detect_mime_type(image_bytes)
            contents.append(
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type,
                )
            )

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ScheduleMatch,
        )

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config,
        )

        if response.parsed:
            return response.parsed

        try:
            return ScheduleMatch.model_validate_json(response.text)
        except ValidationError as error:
            raise GeminiResponseError(
                "Gemini returned a response that does not match the required JSON schema."
            ) from error
