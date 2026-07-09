#include "MacroMesh.hpp"

// Declare the explicit template instantiations via a macro. cppwg's source-text
// scan does not expand macros and so will not find these; they are instead
// discovered via the pygccxml (CastXML) fallback.
#define INSTANTIATE_MACROMESH(ELEMENT_DIM, SPACE_DIM) template class MacroMesh<ELEMENT_DIM, SPACE_DIM>;

INSTANTIATE_MACROMESH(2, 2)
INSTANTIATE_MACROMESH(3, 3)
