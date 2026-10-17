
import base64
import io
import time
from typing import Literal

import matplotlib
import matplotlib.pyplot as plt

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.core.matplotlibVisualizer import plot_feasible_region
from backend.core.simplex_engine import SimplexSolver
app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}

# Force Matplotlib to use a non-GUI headless backend for web servers
matplotlib.use("Agg")
app = FastAPI(

    title="Simplex Method API",

    description="Strictly-typed FastAPI backend for 2D/3D Revised Simplex & Big-M",

    version="1.0.0",

)


# Allow React dev server (and deployed frontend) to talk to FastAPI

app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],  # In production, you can restrict to your Vercel domain

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)



class SimplexRequest(BaseModel):

    c: list[float] = Field(..., description="Objective function coefficients")

    A: list[list[float]] = Field(..., description="Constraint matrix (m x n)")

    b: list[float] = Field(..., description="Right-hand side values")

    inequalities: list[Literal["<=", ">="]] = Field(

        ..., description="Inequality sign for each constraint"

    )

    maximize: bool = Field(True, description="True for Maximize, False for Minimize")



class SimplexResponse(BaseModel):

    status: str

    optimal_z: float

    optimal_variables: list[float]

    execution_time_ms: float

    plot_base64: str | None = None



@app.get("/health")

def health_check() -> dict[str, str]:

    return {"status": "ok"}



@app.post("/solve", response_model=SimplexResponse)

def solve_simplex(payload: SimplexRequest) -> SimplexResponse:

    num_vars: int = len(payload.c)

    num_constraints: int = len(payload.b)


    if num_vars not in (2, 3):

        raise HTTPException(

            status_code=400, detail="Only 2D (2 variables) and 3D (3 variables) are supported."

        )

    if len(payload.A) != num_constraints or len(payload.inequalities) != num_constraints:

        raise HTTPException(

            status_code=400,

            detail="Dimension mismatch between A, b, and inequalities.",

        )


    start_time: float = time.perf_counter()


    solver = SimplexSolver(

        obj_coefficients=payload.c,

        constraint_matrix=payload.A,

        rhs_values=payload.b,

        maximize=payload.maximize,

        inequalities=list(payload.inequalities),

    )

    final_b_star, final_z, status = solver.solve()


    elapsed_ms: float = (time.perf_counter() - start_time) * 1000.0


    # Reconstruct decision variables [x1, x2] or [x1, x2, x3] from basic_indices

    optimal_vars: list[float] = [0.0] * num_vars

    for row_idx, var_idx in enumerate(solver.basic_indices):

        if var_idx < num_vars:

            optimal_vars[var_idx] = float(final_b_star[row_idx])


    # Generate 2D Matplotlib Plot if 2 variables and a valid solution exists

    plot_b64: str | None = None

    if num_vars == 2 and status == "Optimal Solution Found":

        fig, ax = plt.subplots(figsize=(6, 5), dpi=120)

        plot_feasible_region(

            ax=ax,

            c=payload.c,

            A=payload.A,

            b=payload.b,

            inequalities=list(payload.inequalities),

            optimal_point=optimal_vars,

            max_z=final_z,

        )

        fig.tight_layout()


        buf = io.BytesIO()

        fig.savefig(buf, format="png")

        plt.close(fig)

        buf.seek(0)

        plot_b64 = base64.b64encode(buf.read()).decode("utf-8")


    return SimplexResponse(

        status=status,

        optimal_z=round(final_z, 4),

        optimal_variables=[round(v, 4) for v in optimal_vars],

        execution_time_ms=round(elapsed_ms, 3),

        plot_base64=plot_b64,

    )
