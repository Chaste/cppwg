#ifndef PETSC_UTILS_HPP_
#define PETSC_UTILS_HPP_

#include <petsc.h>
#include <petscvec.h>
#include <petscmat.h>
#include <petscsys.h>

#include <vector>

class PetscUtils
{
public:
    static void Initialise();

    static bool IsInitialised();

    static int GetSize();
    static int GetRank();

    static Vec CreateVec(int size);

    /** Throw a C++ exception on a bad PETSc error code (see .cpp). */
    static void ThrowPetscError();
};

#endif // PETSC_UTILS_HPP_
